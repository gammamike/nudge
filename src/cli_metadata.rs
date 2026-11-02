//! Read-only, locale-stable CLI metadata and literal option arity.

use std::collections::BTreeMap;
use std::env;
use std::fs;
use std::hash::{DefaultHasher, Hash, Hasher};
use std::os::unix::fs::{MetadataExt, PermissionsExt};
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};
use std::time::{Duration, SystemTime, UNIX_EPOCH};

use anyhow::{Context, Result, ensure};
use regex::Regex;
use serde::{Deserialize, Serialize};

use crate::catalog;
use crate::process::Runner;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum Arity {
    None,
    Required,
    Optional,
}
pub(crate) type Flags = BTreeMap<String, Arity>;

pub(crate) fn executable(name: &str) -> Option<PathBuf> {
    env::split_paths(&env::var_os("PATH").unwrap_or_default()).find_map(|directory| {
        let path = directory.join(name);
        let metadata = fs::metadata(&path).ok()?;
        (metadata.is_file() && metadata.permissions().mode() & 0o111 != 0)
            // Preserve the basename: rustup and BusyBox select behavior from
            // argv[0]. Canonicalizing their symlinks invokes a different CLI.
            .then(|| std::path::absolute(path).ok())
            .flatten()
    })
}

#[derive(Deserialize, Serialize)]
struct CachedHelp {
    created: u64,
    text: String,
}

pub(crate) fn capture(executable: &Path, args: &[String], runner: &Runner) -> Result<String> {
    capture_status(executable, args, runner, &[0, 129])
}

fn capture_status(
    executable: &Path,
    args: &[String],
    runner: &Runner,
    statuses: &[i32],
) -> Result<String> {
    let output = runner.run(
        Command::new(executable)
            .args(args)
            .env("LC_ALL", "C")
            .env("NO_COLOR", "1")
            .env("TERM", "dumb")
            .env("GIT_PAGER", "cat")
            .env("SYSTEMD_PAGER", "cat")
            .env("SYSTEMD_COLORS", "0")
            .env("PAGER", "cat")
            .env("MANPAGER", "cat")
            .env("NIX_PAGER", "cat")
            .stdin(Stdio::null()),
        Duration::from_secs(5),
    )?;
    // Git's -h is a read-only usage request and exits 129 for many commands.
    ensure!(
        output
            .status
            .code()
            .is_some_and(|code| statuses.contains(&code)),
        "command metadata unavailable"
    );
    Ok(format!("{}\n{}", output.stdout, output.stderr))
}

pub(crate) fn help(
    executable: &Path,
    args: &[String],
    cache: &Path,
    runner: &Runner,
) -> Result<String> {
    help_status(executable, args, cache, runner, &[0, 129])
}

pub(crate) fn help_status(
    executable: &Path,
    args: &[String],
    cache: &Path,
    runner: &Runner,
    statuses: &[i32],
) -> Result<String> {
    let metadata = fs::metadata(executable)?;
    let mut hasher = DefaultHasher::new();
    (
        "cli-help-v2",
        executable,
        metadata.mtime(),
        metadata.mtime_nsec(),
        metadata.len(),
        args,
        statuses,
    )
        .hash(&mut hasher);
    // Compose is a separate plugin whose version can change independently.
    if args.first().is_some_and(|arg| arg == "compose") {
        capture(
            executable,
            &["compose".into(), "version".into(), "--short".into()],
            runner,
        )?
        .hash(&mut hasher);
    }
    if args.first().is_some_and(|arg| arg == "buildx") {
        capture(executable, &["buildx".into(), "version".into()], runner)?.hash(&mut hasher);
    }
    let file = cache.join(format!("cli-{:016x}.json", hasher.finish()));
    let now = SystemTime::now().duration_since(UNIX_EPOCH)?.as_secs();
    if let Ok(bytes) = fs::read(&file)
        && let Ok(saved) = serde_json::from_slice::<CachedHelp>(&bytes)
        && saved.created <= now
        && now - saved.created < 3600
    {
        return Ok(saved.text);
    }
    let text = capture_status(executable, args, runner, statuses)?;
    ensure!(text.len() <= 1_048_576, "command metadata too large");
    catalog::create_cache(cache)?;
    let mut temporary = tempfile::NamedTempFile::new_in(cache)?;
    serde_json::to_writer(
        &mut temporary,
        &CachedHelp {
            created: now,
            text: text.clone(),
        },
    )?;
    temporary.persist(file)?;
    Ok(text)
}

pub(crate) fn commands(help: &str) -> Result<Vec<String>> {
    let pattern = Regex::new(r"^  \[?([a-z][a-z0-9-]*)\*?(?:\s|\[)")?;
    let mut names: Vec<_> = help
        .lines()
        .filter_map(|line| pattern.captures(line).map(|c| c[1].to_owned()))
        .collect();
    names.sort();
    names.dedup();
    ensure!(!names.is_empty(), "no command definitions discovered");
    Ok(names)
}

pub(crate) fn flags(help: &str) -> Result<Flags> {
    let names = Regex::new(r"--(?:\[no-\])?[a-zA-Z][a-zA-Z0-9-]*|-[a-zA-Z0-9]")?;
    let value = Regex::new(
        r"(?:=|<|\s(?:[A-Z][A-Z0-9_…|]*|string\w*|int\w*|uint\w*|duration|list|bytes)\b)",
    )?;
    let mut flags = Flags::new();
    for line in help.lines() {
        let line = line.trim_start();
        if !line.starts_with('-') {
            continue;
        }
        let syntax = line.split("  ").next().unwrap_or(line);
        let arity = if syntax.contains("[=") {
            Arity::Optional
        } else if value.is_match(syntax) {
            Arity::Required
        } else {
            Arity::None
        };
        for item in names.find_iter(syntax) {
            let name = item.as_str();
            if let Some(rest) = name.strip_prefix("--[no-]") {
                flags.insert(format!("--{rest}"), arity);
                flags.insert(format!("--no-{rest}"), Arity::None);
            } else {
                flags.insert(name.to_owned(), arity);
            }
        }
    }
    Ok(flags)
}

// Returns the next argv index. Unknown flags return None; positional values
// and '--' are handled by the caller. Values are never corrected.
pub(crate) fn consume(
    words: &[String],
    index: usize,
    flags: &Flags,
    abbreviate: bool,
) -> Option<usize> {
    let word = words.get(index)?;
    if word.starts_with("--") {
        let (name, attached) = word
            .split_once('=')
            .map_or((word.as_str(), false), |(name, _)| (name, true));
        let arity = flags.get(name).copied().or_else(|| {
            if !abbreviate {
                return None;
            }
            let matches: Vec<_> = flags
                .iter()
                .filter(|(flag, _)| flag.starts_with(name))
                .collect();
            (matches.len() == 1).then(|| *matches[0].1)
        })?;
        if !attached
            && arity == Arity::Optional
            && matches!(name, "--lines" | "--boot")
            && words
                .get(index + 1)
                .is_some_and(|v| v.parse::<i64>().is_ok())
        {
            return Some(index + 2);
        }
        return advance(words, index, arity, attached);
    }
    let mut chars = word.strip_prefix('-')?.chars().peekable();
    while let Some(c) = chars.next() {
        let arity = *flags.get(&format!("-{c}"))?;
        if arity == Arity::Optional
            && matches!(c, 'n' | 'b')
            && chars.peek().is_none()
            && words
                .get(index + 1)
                .is_some_and(|v| v.parse::<i64>().is_ok())
        {
            return Some(index + 2);
        }
        if arity != Arity::None {
            return advance(words, index, arity, chars.peek().is_some());
        }
    }
    Some(index + 1)
}

fn advance(words: &[String], index: usize, arity: Arity, attached: bool) -> Option<usize> {
    match (arity, attached) {
        (Arity::None, true) => None,
        (_, true) | (Arity::None | Arity::Optional, false) => Some(index + 1),
        (Arity::Required, false) => (index + 1 < words.len()).then_some(index + 2),
    }
}

pub(crate) fn definition(
    root: &Path,
    route: &[String],
    cache: &Path,
    runner: &Runner,
    git: bool,
) -> Result<Flags> {
    let mut args = route.to_vec();
    args.push(if git { "-h" } else { "--help" }.to_owned());
    let mut flags =
        flags(&help(root, &args, cache, runner)?).context("cannot validate command options")?;
    // Git's short help omits shared revision/diff flags. These established
    // Git 2.x options supplement discovery only for the listed builtins.
    if git
        && route
            .first()
            .is_some_and(|v| matches!(v.as_str(), "log" | "show"))
    {
        for name in [
            "--oneline",
            "--graph",
            "--all",
            "--reverse",
            "--first-parent",
            "--no-merges",
            "--merges",
            "--date-order",
            "--topo-order",
            "--follow",
            "--patch",
            "-p",
            "--stat",
            "--name-only",
            "--name-status",
        ] {
            flags.entry(name.into()).or_insert(Arity::None);
        }
        for name in [
            "-n",
            "--max-count",
            "--since",
            "--until",
            "--author",
            "--grep",
            "--format",
            "--date",
        ] {
            flags.entry(name.into()).or_insert(Arity::Required);
        }
        for name in ["--pretty", "--branches", "--tags", "--remotes"] {
            flags.entry(name.into()).or_insert(Arity::Optional);
        }
    }
    if git && route.first().is_some_and(|v| v == "diff") {
        for name in ["--cached", "--staged", "--check", "--no-index"] {
            flags.entry(name.into()).or_insert(Arity::None);
        }
    }
    Ok(flags)
}
