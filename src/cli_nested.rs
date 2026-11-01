//! Scoped grammars for nested commands, resource selectors, and command payloads.

use std::collections::{BTreeMap, BTreeSet};
use std::path::Path;
use std::sync::OnceLock;

use anyhow::{Context as _, Result};
use regex::Regex;
use serde::Deserialize;

use crate::cli_adapters::{Analysis, Problem};
use crate::cli_metadata as metadata;
use crate::engine::{self, Options};
use crate::process::Runner;

#[derive(Clone, Copy, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "kebab-case")]
enum Kind {
    Generic,
    Nix,
    Iwctl,
    Zellij,
    Strace,
}

#[derive(Default, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "kebab-case")]
enum Payload {
    #[default]
    None,
    AfterSeparator,
    RequireSeparator,
    FirstOperand,
}

#[derive(Default, Deserialize)]
#[serde(deny_unknown_fields)]
struct Node {
    #[serde(default)]
    help: Vec<String>,
    #[serde(default)]
    extra_help: Vec<Vec<String>>,
    #[serde(default)]
    flags: String,
    #[serde(default)]
    commands: BTreeMap<String, Node>,
    #[serde(default)]
    aliases: Vec<String>,
    #[serde(default)]
    metadata_path: Option<Vec<String>>,
    #[serde(default)]
    min: usize,
    #[serde(default)]
    max: Option<usize>,
    #[serde(default)]
    payload: Payload,
    #[serde(default)]
    known_aliases: Vec<String>,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Profile {
    kind: Kind,
    root: Node,
}

fn registry() -> &'static BTreeMap<String, Profile> {
    static PROFILES: OnceLock<BTreeMap<String, Profile>> = OnceLock::new();
    PROFILES.get_or_init(|| {
        serde_json::from_str(include_str!("../data/nested-profiles.json"))
            .expect("embedded, tested nested CLI registry must be valid")
    })
}

pub(crate) fn roots() -> impl Iterator<Item = &'static str> {
    registry().keys().map(String::as_str)
}

pub(crate) fn supports(root: &str) -> bool {
    registry().contains_key(root)
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
enum Arity {
    Count(usize),
    Optional,
    Rest,
}

type Flags = BTreeMap<String, Arity>;

fn declarations(spec: &str) -> Flags {
    // Bare flags take no value; = and =2 take fixed values, ? accepts an
    // attached optional value, and * consumes an opaque command payload.
    spec.split_whitespace()
        .map(|item| {
            let (name, arity) = if let Some(name) = item.strip_suffix("=2") {
                (name, Arity::Count(2))
            } else if let Some(name) = item.strip_suffix('=') {
                (name, Arity::Count(1))
            } else if let Some(name) = item.strip_suffix('?') {
                (name, Arity::Optional)
            } else if let Some(name) = item.strip_suffix('*') {
                (name, Arity::Rest)
            } else {
                (item, Arity::Count(0))
            };
            (name.to_owned(), arity)
        })
        .collect()
}

fn plain_help(text: &str) -> String {
    static ANSI: OnceLock<Regex> = OnceLock::new();
    let text = ANSI
        .get_or_init(|| Regex::new(r"\x1b\[[0-?]*[ -/]*[@-~]").expect("literal regex"))
        .replace_all(text, "");
    let mut plain = String::new();
    for c in text.chars() {
        if c == '\x08' {
            plain.pop();
        } else {
            plain.push(c);
        }
    }
    plain
}

fn flag_names(text: &str) -> BTreeSet<String> {
    static NAMES: OnceLock<Regex> = OnceLock::new();
    NAMES
        .get_or_init(|| Regex::new(r"--?[a-zA-Z][a-zA-Z0-9_-]*").expect("literal regex"))
        .find_iter(text)
        .map(|item| item.as_str().to_owned())
        .collect()
}

fn command_names(text: &str) -> BTreeSet<String> {
    static COMMANDS: OnceLock<Regex> = OnceLock::new();
    static ALIASES: OnceLock<Regex> = OnceLock::new();
    static COBRA_ALIASES: OnceLock<Regex> = OnceLock::new();
    let mut names: BTreeSet<_> = COMMANDS
        .get_or_init(|| {
            Regex::new(r"(?m)^[ \t]{2,}([a-z][a-z0-9-]*(?:, [a-z][a-z0-9-]*)*):?[ \t]{2,}")
                .expect("literal regex")
        })
        .captures_iter(text)
        .flat_map(|c| c[1].split(", ").map(str::to_owned).collect::<Vec<_>>())
        .collect();
    for c in ALIASES
        .get_or_init(|| Regex::new(r"\[alias(?:es)?: ([^\]]+)\]").expect("literal regex"))
        .captures_iter(text)
    {
        names.extend(c[1].split(',').map(|s| s.trim().to_owned()));
    }
    for c in COBRA_ALIASES
        .get_or_init(|| Regex::new(r"(?m)^Aliases:\n[ \t]+([^\n]+)").expect("literal regex"))
        .captures_iter(text)
    {
        names.extend(c[1].split(',').map(|s| s.trim().to_owned()));
    }
    names
}

#[derive(Deserialize)]
struct NixFlag {
    arity: Option<usize>,
    #[serde(rename = "shortName")]
    short: Option<String>,
}

#[derive(Deserialize)]
struct NixNode {
    #[serde(default)]
    commands: BTreeMap<String, NixNode>,
    flags: BTreeMap<String, NixFlag>,
}

#[derive(Deserialize)]
struct NixDump {
    args: NixNode,
}

impl NixNode {
    fn at(&self, path: &[String]) -> Option<&Self> {
        path.iter()
            .try_fold(self, |node, name| node.commands.get(name))
    }

    fn flags(&self) -> Flags {
        let mut flags = Flags::new();
        for (name, flag) in &self.flags {
            let arity = flag.arity.map_or(Arity::Rest, Arity::Count);
            flags.insert(format!("--{name}"), arity);
            if let Some(short) = &flag.short {
                flags.insert(format!("-{short}"), arity);
            }
        }
        flags
    }
}

struct Evidence {
    flags: Flags,
    known_flags: BTreeSet<String>,
    commands: BTreeSet<String>,
}

struct Context<'a> {
    words: &'a [String],
    executable: &'a Path,
    options: &'a Options<'a>,
    runner: &'a Runner,
    kind: Kind,
    nix: Option<NixDump>,
}

impl Context<'_> {
    fn evidence(&self, node: &Node, route: &[String]) -> Result<Evidence> {
        let declared = declarations(&node.flags);
        if let Some(dump) = &self.nix {
            let actual = dump
                .args
                .at(route)
                .or_else(|| {
                    node.metadata_path
                        .as_deref()
                        .and_then(|path| dump.args.at(path))
                })
                .context("Nix command absent from metadata")?;
            let actual_flags = actual.flags();
            let flags = declared
                .into_iter()
                .filter(|(name, arity)| actual_flags.get(name) == Some(arity))
                .collect();
            let mut commands: BTreeSet<_> = actual.commands.keys().cloned().collect();
            commands.extend(node.known_aliases.iter().cloned());
            for (name, child) in &node.commands {
                if child
                    .metadata_path
                    .as_deref()
                    .is_some_and(|path| dump.args.at(path).is_some())
                {
                    commands.insert(name.clone());
                }
            }
            return Ok(Evidence {
                flags,
                known_flags: actual_flags.into_keys().collect(),
                commands,
            });
        }
        let mut text =
            metadata::help(self.executable, &node.help, self.options.cache, self.runner)?;
        for query in &node.extra_help {
            text.push('\n');
            text.push_str(&metadata::help(
                self.executable,
                query,
                self.options.cache,
                self.runner,
            )?);
        }
        let text = plain_help(&text);
        let known_flags = flag_names(&text);
        let flags = declared
            .into_iter()
            .filter(|(name, _)| known_flags.contains(name))
            .collect();
        Ok(Evidence {
            flags,
            known_flags,
            commands: command_names(&text),
        })
    }

    fn walk(
        &self,
        node: &Node,
        mut index: usize,
        route: &[String],
        inherited: &Flags,
        inherited_known: &BTreeSet<String>,
    ) -> Result<Analysis> {
        let mut evidence = self.evidence(node, route)?;
        if self.kind == Kind::Nix || self.words[0] == "kubectl" {
            for (name, arity) in inherited {
                evidence.flags.entry(name.clone()).or_insert(*arity);
            }
            evidence.known_flags.extend(inherited_known.iter().cloned());
        }
        let syntax: Vec<_> = std::iter::once(self.words[0].clone())
            .chain(route.iter().cloned())
            .collect();
        let mut scanner = Scanner::new(self.words, self.kind, &evidence, &syntax);
        let scan = scanner.scan(index, node, !node.commands.is_empty());
        if let Some(issue) = scan.issue {
            return Ok(issue);
        }
        index = scan.next;
        if node.commands.is_empty() {
            return Ok(
                if (self.kind == Kind::Strace
                    && !scan.has_payload
                    && !scanner.seen.iter().any(|s| {
                        matches!(
                            s.as_str(),
                            "-p" | "--attach" | "-h" | "--help" | "-V" | "--version"
                        )
                    }))
                    || scan.operands < node.min
                    || node.max.is_some_and(|max| scan.operands > max)
                    || (node.payload == Payload::RequireSeparator && !scan.has_payload)
                {
                    Analysis::Refuse
                } else {
                    Analysis::Valid
                },
            );
        }
        let Some(word) = self.words.get(index) else {
            return Ok(Analysis::Refuse);
        };
        // Kubectl plugins are real commands even when root help omits them.
        // Check only executable existence; never run a user-supplied route.
        if self.words[0] == "kubectl"
            && route.is_empty()
            && engine::command_word(word)
            && metadata::executable(&format!("kubectl-{word}")).is_some()
        {
            return Ok(Analysis::Refuse);
        }
        // Some CLIs advertise aliases only in the leaf's help. Probe only a
        // reviewed literal query, and require the parent to advertise its name.
        for (name, child) in &node.commands {
            if child.aliases.contains(word) && evidence.commands.contains(name) {
                let aliases = self.evidence(child, route)?.commands;
                if aliases.contains(word) && aliases.contains(name) {
                    evidence.commands.insert(word.clone());
                }
            }
        }
        let child = node.commands.iter().find(|(name, child)| {
            (word == *name && evidence.commands.contains(*name))
                || (child.aliases.contains(word)
                    && evidence.commands.contains(word)
                    && evidence.commands.contains(*name))
        });
        let Some((name, child)) = child else {
            let choices: Vec<_> = node
                .commands
                .keys()
                .filter(|name| evidence.commands.contains(*name))
                .cloned()
                .collect();
            // Generic nested grammars intentionally handle local typos only.
            // Unknown extension names or absent destructive commands must not
            // become model requests for unrelated inspection commands.
            if self.kind == Kind::Generic
                && choices
                    .iter()
                    .filter(|name| engine::typo(word, name) == 1)
                    .count()
                    != 1
            {
                return Ok(Analysis::Refuse);
            }
            return Ok(problem(
                self.words,
                index,
                choices,
                &evidence.commands,
                &syntax,
                false,
                false,
            ));
        };
        let mut route = route.to_vec();
        route.push(name.clone());
        self.walk(
            child,
            index + 1,
            &route,
            &evidence.flags,
            &evidence.known_flags,
        )
    }
}

fn problem(
    words: &[String],
    index: usize,
    choices: Vec<String>,
    known: &BTreeSet<String>,
    syntax: &[String],
    flag: bool,
    abbreviate: bool,
) -> Analysis {
    let original = if flag {
        words[index].split('=').next().unwrap_or(&words[index])
    } else {
        &words[index]
    };
    if (!flag && !engine::command_word(original))
        || known.iter().any(|word| {
            word == original
                || (abbreviate && word.starts_with(original))
                || (engine::typo(original, word) == 1 && !choices.contains(word))
        })
    {
        return Analysis::Refuse;
    }
    let mut syntax = syntax.to_vec();
    syntax.push(original.to_owned());
    Analysis::Problem(Problem {
        index,
        choices,
        syntax,
        flag,
    })
}

struct Scan {
    next: usize,
    operands: usize,
    has_payload: bool,
    issue: Option<Analysis>,
}

struct Scanner<'a> {
    words: &'a [String],
    kind: Kind,
    evidence: &'a Evidence,
    syntax: &'a [String],
    seen: BTreeSet<String>,
}

impl<'a> Scanner<'a> {
    fn new(words: &'a [String], kind: Kind, evidence: &'a Evidence, syntax: &'a [String]) -> Self {
        Self {
            words,
            kind,
            evidence,
            syntax,
            seen: BTreeSet::new(),
        }
    }

    fn scan(&mut self, index: usize, node: &Node, leading: bool) -> Scan {
        let mut result = Scan {
            next: index,
            operands: 0,
            has_payload: false,
            issue: None,
        };
        while result.next < self.words.len() {
            let i = result.next;
            let word = &self.words[i];
            if word == "--" {
                if leading {
                    result.issue = Some(Analysis::Refuse);
                    return result;
                }
                if node.payload == Payload::None {
                    result.operands += self.words.len() - i - 1;
                } else {
                    result.has_payload = i + 1 < self.words.len() && !self.words[i + 1].is_empty();
                    if i + 1 < self.words.len() && !result.has_payload {
                        result.issue = Some(Analysis::Refuse);
                    }
                }
                result.next = self.words.len();
                return result;
            }
            if !word.starts_with('-') || word == "-" {
                if leading {
                    return result;
                }
                if node.payload == Payload::FirstOperand {
                    result.has_payload = !word.is_empty();
                    if !result.has_payload {
                        result.issue = Some(Analysis::Refuse);
                    }
                    result.next = self.words.len();
                    return result;
                }
                result.operands += 1;
                result.next += 1;
                continue;
            }
            if let Some((next, rest)) = self.option(i) {
                result.next = next;
                if rest {
                    result.has_payload = true;
                    return result;
                }
                continue;
            }
            let name = word.split('=').next().unwrap_or(word);
            result.issue = Some(
                if self.evidence.flags.contains_key(name) || !word.starts_with("--") {
                    Analysis::Refuse
                } else {
                    let choices = self
                        .evidence
                        .flags
                        .keys()
                        .filter(|name| name.starts_with("--"))
                        .cloned()
                        .collect();
                    problem(
                        self.words,
                        i,
                        choices,
                        &self.evidence.known_flags,
                        self.syntax,
                        true,
                        self.kind == Kind::Strace,
                    )
                },
            );
            return result;
        }
        result
    }

    fn option(&mut self, index: usize) -> Option<(usize, bool)> {
        let word = &self.words[index];
        if word.starts_with("--") {
            let (name, value) = word
                .split_once('=')
                .map_or((word.as_str(), None), |(name, value)| (name, Some(value)));
            return self.consume(index, name, value);
        }
        let tail = word.strip_prefix('-')?;
        for (offset, c) in tail.char_indices() {
            let name = format!("-{c}");
            let arity = *self.evidence.flags.get(&name)?;
            if arity == Arity::Count(0) {
                self.seen.insert(name);
                continue;
            }
            let after = &tail[offset + c.len_utf8()..];
            return self.consume(index, &name, (!after.is_empty()).then_some(after));
        }
        Some((index + 1, false))
    }

    fn consume(
        &mut self,
        index: usize,
        name: &str,
        attached: Option<&str>,
    ) -> Option<(usize, bool)> {
        let arity = *self.evidence.flags.get(name)?;
        let next = match arity {
            Arity::Count(0) if attached.is_some() => return None,
            Arity::Count(0) | Arity::Optional => index + 1,
            Arity::Count(1) => {
                let value = attached.or_else(|| self.words.get(index + 1).map(String::as_str))?;
                if !self.safe_value(name, value) {
                    return None;
                }
                index + if attached.is_some() { 1 } else { 2 }
            }
            Arity::Count(count) => {
                if attached.is_some() || index + count >= self.words.len() {
                    return None;
                }
                index + count + 1
            }
            Arity::Rest => {
                if attached.is_some() || self.words.get(index + 1).is_none_or(String::is_empty) {
                    return None;
                }
                self.seen.insert(name.to_owned());
                return Some((self.words.len(), true));
            }
        };
        self.seen.insert(name.to_owned());
        Some((next, false))
    }

    fn safe_value(&self, name: &str, value: &str) -> bool {
        if self.kind != Kind::Strace {
            return true;
        }
        match name {
            "-e" => value.split_once('=').is_none_or(|(qualifier, _)| {
                [
                    "trace",
                    "t",
                    "abbrev",
                    "a",
                    "verbose",
                    "v",
                    "raw",
                    "x",
                    "signal",
                    "signals",
                    "s",
                    "read",
                    "reads",
                    "r",
                    "write",
                    "writes",
                    "w",
                    "status",
                    "quiet",
                    "silent",
                    "silence",
                    "q",
                    "decode-fds",
                    "decode-pids",
                    "namespace",
                    "kvm",
                    "trace-fds",
                    "trace-fd",
                    "fd",
                    "fds",
                ]
                .contains(&qualifier)
            }),
            "-p" | "--attach" => value.parse::<u32>().is_ok_and(|pid| pid > 0),
            "-o" | "--output" => !value.is_empty() && !value.starts_with(['|', '!']),
            "-s" | "--string-limit" | "--stack-trace-frame-limit" | "--syscall-limit" => {
                value.parse::<u64>().is_ok()
            }
            _ => true,
        }
    }
}

fn iwctl(context: &Context<'_>, root: &Node) -> Result<Analysis> {
    let text = plain_help(&metadata::help(
        context.executable,
        &root.help,
        context.options.cache,
        context.runner,
    )?);
    let mut evidence = context.evidence(root, &[])?;
    let mut routes: BTreeMap<String, BTreeSet<String>> = BTreeMap::new();
    let pattern = Regex::new(r"^  ([a-z][a-z-]*)\s+(?:<[^>]+>\s+)?([a-z][a-z_-]*)\s")?;
    for line in text.lines() {
        if let Some(c) = pattern.captures(line) {
            routes
                .entry(c[1].to_owned())
                .or_default()
                .insert(c[2].to_owned());
        }
    }
    evidence.commands = routes.keys().cloned().collect();
    let base = vec!["iwctl".to_owned()];
    let mut scanner = Scanner::new(context.words, Kind::Iwctl, &evidence, &base);
    let scan = scanner.scan(1, root, true);
    if let Some(issue) = scan.issue {
        return Ok(issue);
    }
    let group_index = scan.next;
    let Some(group) = context.words.get(group_index) else {
        return Ok(Analysis::Refuse);
    };
    let Some(node) = root
        .commands
        .get(group)
        .filter(|_| routes.contains_key(group))
    else {
        return Ok(problem(
            context.words,
            group_index,
            root.commands
                .keys()
                .filter(|s| routes.contains_key(*s))
                .cloned()
                .collect(),
            &evidence.commands,
            &base,
            false,
            false,
        ));
    };
    let known = &routes[group];
    let tail = &context.words[group_index + 1..];
    if tail.len() == 1 {
        if !known.contains("list") {
            return Ok(Analysis::Refuse);
        }
        if tail[0] == "list" {
            return Ok(Analysis::Valid);
        }
        // With no action word, this could be an incomplete device/SSID argument.
        // Only a unique local typo of `list` is eligible; never send it to AI.
        if engine::typo(&tail[0], "list") != 1 {
            return Ok(Analysis::Refuse);
        }
        return Ok(problem(
            context.words,
            group_index + 1,
            vec!["list".into()],
            known,
            &["iwctl".into(), group.clone()],
            true,
            false,
        ));
    }
    if tail.len() < 2 || tail[0].is_empty() || tail[0].starts_with('-') || tail[0] == "list" {
        return Ok(Analysis::Refuse);
    }
    let action = &tail[1];
    let syntax = vec!["iwctl".to_owned(), group.clone()];
    let Some(action_node) = node.commands.get(action).filter(|_| known.contains(action)) else {
        let choices = node
            .commands
            .keys()
            .filter(|s| s.as_str() != "list" && known.contains(*s))
            .cloned()
            .collect();
        return Ok(problem(
            context.words,
            group_index + 2,
            choices,
            known,
            &syntax,
            false,
            false,
        ));
    };
    let count = tail.len() - 2;
    Ok(
        if action == "list"
            || count < action_node.min
            || action_node.max.is_some_and(|max| count > max)
            || tail[2..].iter().any(|s| s.is_empty() || s.starts_with('-'))
        {
            Analysis::Refuse
        } else {
            Analysis::Valid
        },
    )
}

pub(crate) fn analyze(
    words: &[String],
    executable: &Path,
    options: &Options<'_>,
    runner: &Runner,
) -> Result<Analysis> {
    let profile = &registry()[&words[0]];
    let nix = if profile.kind == Kind::Nix {
        Some(
            serde_json::from_str::<NixDump>(&metadata::help(
                executable,
                &profile.root.help,
                options.cache,
                runner,
            )?)
            .context("unsupported Nix command metadata")?,
        )
    } else {
        None
    };
    let context = Context {
        words,
        executable,
        options,
        runner,
        kind: profile.kind,
        nix,
    };
    if profile.kind == Kind::Iwctl {
        return iwctl(&context, &profile.root);
    }
    context.walk(&profile.root, 1, &[], &Flags::new(), &BTreeSet::new())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn terminal_formatting_is_removed_before_metadata_matching() {
        assert_eq!(
            plain_help("\x1b[90m  station\x1b[0m _\x08s_\x08h_\x08o_\x08w"),
            "  station show"
        );
        assert_eq!(plain_help("b\x08bu\x08ui\x08il\x08ld\x08d"), "build");
    }

    #[test]
    fn registry_queries_and_arities_are_explicit() {
        assert!(registry().len() >= 4);
        fn check(node: &Node, kind: Kind) {
            assert_eq!(
                declarations(&node.flags).len(),
                node.flags.split_whitespace().count()
            );
            assert!(node.max.is_none_or(|max| max >= node.min));
            if matches!(kind, Kind::Zellij | Kind::Generic) {
                assert_eq!(node.help.last().map(String::as_str), Some("--help"));
            }
            for child in node.commands.values() {
                check(child, kind);
            }
        }
        for profile in registry().values() {
            check(&profile.root, profile.kind);
        }
        assert_eq!(
            declarations("--arg=2 --command* --stack-trace?")["--arg"],
            Arity::Count(2)
        );
    }

    #[test]
    fn command_columns_include_advertised_aliases() {
        let names = command_names(
            "Commands:\n   images, image, i   Manage images\n  inspect  Inspect a resource\n  repo:  Repository commands\nAliases:\n  list, ls\n",
        );
        assert_eq!(
            names,
            ["i", "image", "images", "inspect", "list", "ls", "repo"]
                .into_iter()
                .map(str::to_owned)
                .collect()
        );
    }
}
