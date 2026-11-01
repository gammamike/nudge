//! First Linux CLI adapters: correct syntax slots, never resource arguments.

use std::path::Path;
use std::time::Instant;

use anyhow::Result;

use crate::ai::Provider;
use crate::catalog::Entry;
use crate::cli_metadata::{self as metadata, Arity, Flags};
use crate::engine::{self, Options, Suggestion};
use crate::process::Runner;
use crate::{claude, codex, local, shell_words, terminal};

pub(crate) fn supports(root: &str) -> bool {
    matches!(root, "git" | "docker" | "systemctl" | "journalctl")
        || crate::cli_profiles::supports(root)
}

fn eligible(root: &str, parent: &str) -> &'static [&'static str] {
    match (root, parent) {
        ("git", _) => &[
            "status",
            "log",
            "diff",
            "show",
            "blame",
            "grep",
            "describe",
            "shortlog",
            "ls-files",
            "ls-tree",
            "ls-remote",
            "rev-parse",
            "add",
            "commit",
            "fetch",
            "pull",
            "push",
            "clone",
            "init",
            "branch",
            "checkout",
            "switch",
            "merge",
            "rebase",
            "tag",
            "help",
            "version",
        ],
        ("systemctl", _) => &[
            "status",
            "show",
            "cat",
            "help",
            "is-active",
            "is-failed",
            "is-enabled",
            "is-system-running",
            "list-units",
            "list-unit-files",
            "list-timers",
            "list-sockets",
            "list-paths",
            "list-automounts",
            "list-dependencies",
            "list-jobs",
            "list-machines",
            "show-environment",
            "get-default",
            "start",
            "stop",
            "restart",
            "reload",
            "try-restart",
            "reload-or-restart",
            "try-reload-or-restart",
            "daemon-reload",
            "enable",
            "disable",
        ],
        ("docker", "compose") => &[
            "ps", "ls", "logs", "config", "images", "version", "top", "port", "stats", "start",
            "stop", "restart", "pause", "unpause", "build", "pull", "push", "up", "run", "exec",
            "events", "wait",
        ],
        ("docker", "container") => &[
            "ls", "logs", "inspect", "start", "stop", "restart", "stats", "top", "port", "diff",
            "run", "exec", "pause", "unpause", "wait",
        ],
        ("docker", "image") => &["ls", "inspect", "history", "pull", "push", "tag", "build"],
        ("docker", "network" | "volume") => &["ls", "inspect"],
        ("docker", "system") => &["df", "info", "events"],
        ("docker", "") => &[
            "compose",
            "container",
            "image",
            "network",
            "volume",
            "system",
            "ps",
            "images",
            "logs",
            "inspect",
            "info",
            "version",
            "start",
            "stop",
            "restart",
            "stats",
            "top",
            "port",
            "history",
            "events",
            "run",
            "exec",
            "build",
            "pull",
            "push",
            "tag",
            "pause",
            "unpause",
            "wait",
        ],
        _ => &[],
    }
}

pub(crate) struct Problem {
    pub(crate) index: usize,
    pub(crate) choices: Vec<String>,
    pub(crate) syntax: Vec<String>,
    pub(crate) flag: bool,
}

pub(crate) enum Analysis {
    Valid,
    Refuse,
    Problem(Problem),
}

fn blocked_flag(root: &str, command: &str, flag: &str) -> bool {
    let name = flag.split('=').next().unwrap_or(flag);
    if [
        "--force",
        "--delete",
        "--hard",
        "--discard-changes",
        "--overwrite",
        "--prune",
    ]
    .iter()
    .any(|prefix| name == *prefix || name.starts_with(&format!("{prefix}-")))
    {
        return true;
    }
    match root {
        "git" => {
            matches!(
                name,
                "-f" | "-D"
                    | "-B"
                    | "--orphan"
                    | "--overwrite-ignore"
                    | "--ignore-other-worktrees"
                    | "--exec"
            ) || (matches!(command, "branch" | "tag")
                && name.starts_with('-')
                && !name.starts_with("--")
                && name.contains('d'))
        }
        "systemctl" => matches!(name, "--now" | "--no-block"),
        "journalctl" => {
            name.starts_with("--vacuum")
                || matches!(
                    name,
                    "--rotate"
                        | "--flush"
                        | "--sync"
                        | "--relinquish-var"
                        | "--smart-relinquish-var"
                        | "--setup-keys"
                        | "--update-catalog"
                )
        }
        "docker" => matches!(
            name,
            "--privileged" | "--remove-orphans" | "--renew-anon-volumes"
        ),
        _ => false,
    }
}

fn flag_problem(words: &[String], index: usize, flags: &Flags, syntax: &[String]) -> Analysis {
    let word = &words[index];
    if !word.starts_with("--") {
        return Analysis::Refuse;
    }
    let choices = flags
        .keys()
        .filter(|name| {
            name.starts_with("--")
                && !blocked_flag(&words[0], syntax.last().map_or("", String::as_str), name)
        })
        .cloned()
        .collect();
    let mut syntax = syntax.to_vec();
    syntax.push(word.split('=').next().unwrap_or(word).to_owned());
    Analysis::Problem(Problem {
        index,
        choices,
        syntax,
        flag: true,
    })
}

fn scan_flags(
    words: &[String],
    mut index: usize,
    flags: &Flags,
    syntax: &[String],
    leading: bool,
    stop_at_operand: bool,
) -> (usize, Option<Analysis>) {
    while index < words.len() {
        let word = &words[index];
        if words[0] == "git"
            && syntax.last().is_some_and(|v| v == "log")
            && word
                .strip_prefix('-')
                .is_some_and(|v| !v.is_empty() && v.bytes().all(|b| b.is_ascii_digit()))
        {
            index += 1;
            continue;
        }
        if word == "--" {
            return (
                if leading { index } else { words.len() },
                if leading {
                    Some(Analysis::Refuse)
                } else {
                    None
                },
            );
        }
        if !word.starts_with('-') || word == "-" {
            if leading || stop_at_operand {
                break;
            }
            index += 1;
            continue;
        }
        if blocked_flag(&words[0], syntax.last().map_or("", String::as_str), word) {
            return (index, Some(Analysis::Refuse));
        }
        if word.starts_with("--") && words[0] != "docker" {
            let name = word.split('=').next().unwrap_or(word);
            if !flags.contains_key(name) {
                let matches: Vec<_> = flags.keys().filter(|flag| flag.starts_with(name)).collect();
                if matches.len() == 1
                    && blocked_flag(
                        &words[0],
                        syntax.last().map_or("", String::as_str),
                        matches[0],
                    )
                {
                    return (index, Some(Analysis::Refuse));
                }
            }
        }
        if !word.starts_with("--") {
            for c in word[1..].chars() {
                let flag = format!("-{c}");
                if blocked_flag(&words[0], syntax.last().map_or("", String::as_str), &flag) {
                    return (index, Some(Analysis::Refuse));
                }
                if flags.get(&flag) != Some(&Arity::None) {
                    break;
                }
            }
        }
        if let Some(next) = metadata::consume(words, index, flags, words[0] != "docker") {
            index = next;
        } else {
            // An existing option with a missing/invalid value is not a typo.
            let name = word.split('=').next().unwrap_or(word);
            if flags.contains_key(name) {
                return (index, Some(Analysis::Refuse));
            }
            return (index, Some(flag_problem(words, index, flags, syntax)));
        }
    }
    (index, None)
}

fn tail(words: &[String], index: usize, flags: &Flags, syntax: &[String], stop: bool) -> Analysis {
    if let Some(problem) = scan_flags(words, index, flags, syntax, false, stop).1 {
        return problem;
    }
    let root = words[0].as_str();
    let command = syntax.last().map_or("", String::as_str);
    let compose = syntax.get(1).is_some_and(|v| v == "compose");
    let minimum = match root {
        "systemctl"
            if matches!(
                command,
                "start"
                    | "stop"
                    | "restart"
                    | "reload"
                    | "try-restart"
                    | "reload-or-restart"
                    | "try-reload-or-restart"
                    | "enable"
                    | "disable"
                    | "cat"
            ) =>
        {
            1
        }
        "docker" if command == "exec" || command == "tag" => 2,
        "docker" if command == "run" => 1,
        "docker"
            if !compose
                && matches!(
                    command,
                    "logs"
                        | "inspect"
                        | "start"
                        | "stop"
                        | "restart"
                        | "top"
                        | "port"
                        | "history"
                        | "pull"
                        | "push"
                        | "build"
                        | "pause"
                        | "unpause"
                        | "wait"
                ) =>
        {
            1
        }
        "git" if matches!(command, "clone" | "switch" | "blame" | "grep") => 1,
        _ => 0,
    };
    if minimum == 0 {
        return Analysis::Valid;
    }
    let mut count = 0;
    let mut i = index;
    while i < words.len() {
        if words[i] == "--" {
            count += words.len() - i - 1;
            break;
        }
        if words[i].starts_with('-') && words[i] != "-" {
            let Some(next) = metadata::consume(words, i, flags, root != "docker") else {
                return Analysis::Refuse;
            };
            i = next;
        } else {
            if stop {
                count += words.len() - i;
                break;
            }
            count += 1;
            i += 1;
        }
    }
    if count >= minimum {
        Analysis::Valid
    } else {
        Analysis::Refuse
    }
}

fn command_problem(
    words: &[String],
    index: usize,
    known: &[String],
    root: &str,
    parent: &str,
    syntax: &[String],
) -> Analysis {
    if !engine::command_word(&words[index])
        || known.iter().any(|name| {
            engine::typo(&words[index], name) == 1
                && !eligible(root, parent).contains(&name.as_str())
        })
    {
        return Analysis::Refuse;
    }
    let choices = eligible(root, parent)
        .iter()
        .filter(|name| known.iter().any(|item| item == **name))
        .map(|s| (*s).to_owned())
        .collect();
    let mut syntax = syntax.to_vec();
    syntax.push(words[index].clone());
    Analysis::Problem(Problem {
        index,
        choices,
        syntax,
        flag: false,
    })
}

fn analyze(
    words: &[String],
    executable: &Path,
    options: &Options<'_>,
    runner: &Runner,
) -> Result<Analysis> {
    let root = words[0].as_str();
    if crate::cli_profiles::supports(root) {
        return crate::cli_profiles::analyze(words, executable, options, runner);
    }
    let base = vec![words[0].clone()];
    if root == "git" {
        // Configuration-changing global flags are deliberately unsupported.
        let globals: Flags = [
            ("-C", Arity::Required),
            ("--git-dir", Arity::Required),
            ("--work-tree", Arity::Required),
            ("--no-pager", Arity::None),
            ("--paginate", Arity::None),
            ("--literal-pathspecs", Arity::None),
        ]
        .into_iter()
        .map(|(key, value)| (key.to_owned(), value))
        .collect();
        let (index, problem) = scan_flags(words, 1, &globals, &base, true, false);
        if problem.is_some() {
            return Ok(Analysis::Refuse);
        }
        if index >= words.len() {
            return Ok(Analysis::Refuse);
        }
        // Fresh per request, and in the user's selected -C/git-dir context:
        // repository aliases and PATH extensions must never be mistaken for typos.
        let mut args = words[1..index].to_vec();
        args.push("--list-cmds=main,others,alias".to_owned());
        let text = metadata::capture(executable, &args, runner)?;
        let known: Vec<String> = text
            .lines()
            .filter(|line| engine::command_word(line))
            .map(str::to_owned)
            .collect();
        if !known.contains(&words[index]) {
            return Ok(command_problem(words, index, &known, root, "", &base));
        }
        if !eligible(root, "").contains(&words[index].as_str()) {
            return Ok(Analysis::Refuse);
        }
        let flags = metadata::definition(
            executable,
            &[words[index].clone()],
            options.cache,
            runner,
            true,
        )?;
        let syntax = vec![root.to_owned(), words[index].clone()];
        if words[index] == "checkout" && words[index + 1..].iter().any(|v| v == "--") {
            return Ok(Analysis::Refuse);
        }
        return Ok(tail(words, index + 1, &flags, &syntax, false));
    }

    let text = metadata::help(executable, &["--help".into()], options.cache, runner)?;
    let flags = metadata::flags(&text)?;
    if root == "journalctl" {
        return Ok(scan_flags(words, 1, &flags, &base, false, false)
            .1
            .unwrap_or(Analysis::Valid));
    }
    let (mut index, problem) = scan_flags(words, 1, &flags, &base, true, false);
    if let Some(problem) = problem {
        return Ok(problem);
    }
    if index >= words.len() {
        return Ok(Analysis::Refuse);
    }
    // --config changes Docker's plugin resolution; do not probe another config.
    if root == "docker"
        && words[1..index]
            .iter()
            .any(|v| v == "--config" || v.starts_with("--config="))
    {
        return Ok(Analysis::Refuse);
    }
    let known = metadata::commands(&text)?;
    if !known.contains(&words[index]) {
        return Ok(command_problem(words, index, &known, root, "", &base));
    }
    if !eligible(root, "").contains(&words[index].as_str()) {
        return Ok(Analysis::Refuse);
    }
    let mut route = vec![words[index].clone()];
    index += 1;
    if root == "docker"
        && matches!(
            route[0].as_str(),
            "compose" | "container" | "image" | "network" | "volume" | "system"
        )
    {
        let args = vec![route[0].clone(), "--help".into()];
        let help = metadata::help(executable, &args, options.cache, runner)?;
        let globals = metadata::flags(&help)?;
        let syntax = vec![root.to_owned(), route[0].clone()];
        let (next, problem) = scan_flags(words, index, &globals, &syntax, true, false);
        if let Some(problem) = problem {
            return Ok(problem);
        }
        index = next;
        if index >= words.len() {
            return Ok(Analysis::Refuse);
        }
        let known = metadata::commands(&help)?;
        if !known.contains(&words[index]) {
            return Ok(command_problem(
                words, index, &known, root, &route[0], &syntax,
            ));
        }
        if !eligible(root, &route[0]).contains(&words[index].as_str()) {
            return Ok(Analysis::Refuse);
        }
        route.push(words[index].clone());
        index += 1;
    }
    let flags = if root == "systemctl" {
        flags
    } else {
        metadata::definition(executable, &route, options.cache, runner, false)?
    };
    let syntax: Vec<_> = std::iter::once(root.to_owned())
        .chain(route.iter().cloned())
        .collect();
    let stop = root == "docker"
        && route
            .last()
            .is_some_and(|v| matches!(v.as_str(), "run" | "exec"));
    Ok(tail(words, index, &flags, &syntax, stop))
}

fn replace(words: &[String], problem: &Problem, replacement: &str) -> Vec<String> {
    let mut result = words.to_vec();
    result[problem.index] = if problem.flag {
        match words[problem.index].split_once('=') {
            Some((_, value)) => format!("{replacement}={value}"),
            None => replacement.to_owned(),
        }
    } else {
        replacement.to_owned()
    };
    result
}

pub(crate) fn suggest(line: &str, options: &Options<'_>, runner: &Runner) -> Result<Suggestion> {
    let started = Instant::now();
    let mut result = Suggestion {
        command: line.to_owned(),
        suggestion: None,
        source: "none".into(),
        reason: Some("unsupported syntax or no actionable syntax error".into()),
        argv: None,
        executable: None,
        evidence: None,
        elapsed_ms: 0.0,
    };
    let work = (|| -> Result<()> {
        if matches!(options.status, 0 | 130) {
            return Ok(());
        }
        let Some(words) = shell_words::parse(line) else {
            return Ok(());
        };
        let Some(executable) = metadata::executable(&words[0]) else {
            return Ok(());
        };
        let Analysis::Problem(problem) = analyze(&words, &executable, options, runner)? else {
            return Ok(());
        };
        let original = problem.syntax.last().map_or("", String::as_str);
        let close: Vec<_> = problem
            .choices
            .iter()
            .filter(|choice| engine::typo(original, choice) == 1)
            .collect();
        let mut selected = None;
        if close.len() == 1 && !options.force_ai {
            selected = Some(close[0].clone());
            result.source = "local".into();
        } else if !options.local_only && !problem.flag {
            // Only command syntax is sent to AI. Arguments, resource names,
            // option values, paths and config data never leave this adapter.
            let entries: Vec<_> = problem
                .choices
                .iter()
                .map(|choice| {
                    let mut argv = problem.syntax.clone();
                    *argv.last_mut().expect("syntax includes failing command") = choice.clone();
                    Entry {
                        argv,
                        summary: format!("Installed {} command", words[0]),
                        args: String::new(),
                        source: "installed CLI metadata".into(),
                    }
                })
                .collect();
            let choices = entries.iter().collect::<Vec<_>>();
            if choices.is_empty() {
                return Ok(());
            }
            if options.announce {
                terminal::announce(options.provider)?;
            }
            let (entry, reason) = match options.provider {
                Provider::Codex => codex::pick(&problem.syntax, &choices, options, runner)?,
                Provider::Claude => claude::pick(&problem.syntax, &choices, options, runner)?,
                Provider::Ollama | Provider::Local => {
                    local::pick(&problem.syntax, &choices, options, runner)?
                }
            };
            result.source = options.provider.name().into();
            result.reason = reason;
            selected = entry.and_then(|entry| entry.argv.last().cloned());
        }
        if let Some(selected) = selected {
            let corrected = replace(&words, &problem, &selected);
            if matches!(
                analyze(&corrected, &executable, options, runner)?,
                Analysis::Valid
            ) {
                result.suggestion = Some(shell_words::display(&corrected));
                result.argv = Some(corrected);
                result.executable = Some(executable.to_string_lossy().into_owned());
                result.evidence = Some(format!("installed {} command/help metadata", words[0]));
                result.reason = None;
            } else {
                result.reason = Some("correction would leave unsupported or invalid syntax".into());
            }
        }
        Ok(())
    })();
    if let Err(error) = work {
        runner.check_interrupt()?;
        result.reason = Some(format!("CLI metadata unavailable: {error}"));
    }
    result.elapsed_ms = started.elapsed().as_secs_f64() * 1000.0;
    Ok(result)
}
