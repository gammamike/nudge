//! Reviewed Linux grammars, intersected with the installed tool's help.
//!
//! The registry is deliberately explicit: help text supplies evidence, not
//! permission to invent a grammar or probe an arbitrary user-supplied route.

use std::collections::BTreeMap;
use std::path::Path;
use std::sync::OnceLock;

use anyhow::Result;
use regex::Regex;
use serde::Deserialize;

use crate::cli_adapters::{Analysis, Problem};
use crate::cli_metadata::{self as metadata, Arity, Flags};
use crate::engine::{self, Options};
use crate::process::Runner;

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct CommandSpec {
    #[serde(default)]
    min: usize,
    #[serde(default = "unlimited")]
    max: usize,
    #[serde(default)]
    flags: String,
    #[serde(default)]
    help: Vec<String>,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Profile {
    help: Vec<String>,
    #[serde(default)]
    local_only: bool,
    #[serde(default)]
    fresh_commands: Vec<String>,
    #[serde(default = "success")]
    statuses: Vec<i32>,
    flags: String,
    #[serde(default)]
    commands: BTreeMap<String, CommandSpec>,
    #[serde(default)]
    single_dash: bool,
    #[serde(default)]
    abbreviate: bool,
    #[serde(default)]
    stop_at_operand: bool,
    #[serde(default)]
    require_any: Vec<String>,
    #[serde(default = "unlimited")]
    max_operands: usize,
    #[serde(default)]
    min_operands: usize,
}

fn unlimited() -> usize {
    usize::MAX
}

fn success() -> Vec<i32> {
    vec![0]
}

fn registry() -> &'static BTreeMap<String, Profile> {
    static PROFILES: OnceLock<BTreeMap<String, Profile>> = OnceLock::new();
    PROFILES.get_or_init(|| {
        serde_json::from_str(include_str!("../data/linux-profiles.json"))
            .expect("embedded, tested CLI registry must be valid")
    })
}

pub(crate) fn roots() -> impl Iterator<Item = &'static str> {
    registry().keys().map(String::as_str)
}

pub(crate) fn supports(root: &str) -> bool {
    registry().contains_key(root)
}

pub(crate) fn local_only(root: &str) -> bool {
    registry()
        .get(root)
        .is_some_and(|profile| profile.local_only)
}

fn declared(spec: &str) -> Flags {
    spec.split_whitespace()
        .map(|item| {
            let (name, arity) = if let Some(name) = item.strip_suffix('=') {
                (name, Arity::Required)
            } else if let Some(name) = item.strip_suffix('?') {
                (name, Arity::Optional)
            } else {
                (item, Arity::None)
            };
            (name.to_owned(), arity)
        })
        .collect()
}

fn advertised(text: &str) -> Vec<String> {
    static TOKENS: OnceLock<Regex> = OnceLock::new();
    TOKENS
        .get_or_init(|| {
            Regex::new(r"--?[a-zA-Z0-9][a-zA-Z0-9_-]*|[a-zA-Z][a-zA-Z0-9_-]*")
                .expect("literal regex")
        })
        .find_iter(text)
        .map(|item| item.as_str().to_owned())
        .collect()
}

fn evidenced_flags(spec: &str, known: &[String]) -> Flags {
    declared(spec)
        .into_iter()
        .filter(|(name, _)| known.contains(name))
        .collect()
}

fn problem(
    words: &[String],
    index: usize,
    choices: Vec<String>,
    known: &[String],
    syntax: &[String],
    flag: bool,
    abbreviate: bool,
) -> Analysis {
    let original = if flag {
        words[index].split('=').next().unwrap_or(&words[index])
    } else {
        &words[index]
    };
    // Never rewrite an advertised but unreviewed form, a valid abbreviation,
    // or a misspelling that could mean an excluded operation.
    if known.iter().any(|item| {
        item == original
            || (flag && abbreviate && item.starts_with(original))
            || (engine::typo(original, item) == 1 && !choices.contains(item))
    }) {
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

struct Scanner<'a> {
    words: &'a [String],
    profile: &'a Profile,
    flags: &'a Flags,
    known: &'a [String],
    syntax: &'a [String],
}

impl Scanner<'_> {
    fn scan(&self, mut index: usize, leading: bool) -> (usize, usize, Option<Analysis>, bool) {
        let mut operands = 0;
        let mut required_mode = self.profile.require_any.is_empty();
        while index < self.words.len() {
            let word = &self.words[index];
            if word == "--" {
                return if leading {
                    (index, 0, Some(Analysis::Refuse), required_mode)
                } else {
                    (
                        self.words.len(),
                        operands + self.words.len() - index - 1,
                        None,
                        required_mode,
                    )
                };
            }
            if !word.starts_with('-') || word == "-" {
                if leading {
                    break;
                }
                if self.profile.stop_at_operand {
                    return (
                        self.words.len(),
                        operands + self.words.len() - index,
                        None,
                        required_mode,
                    );
                }
                operands += 1;
                index += 1;
                continue;
            }
            let next = if self.profile.single_dash && !word.starts_with("--") {
                self.flags.get(word).and_then(|arity| match arity {
                    Arity::None | Arity::Optional => Some(index + 1),
                    Arity::Required => (index + 1 < self.words.len()).then_some(index + 2),
                })
            } else {
                metadata::consume(self.words, index, self.flags, false)
            };
            if let Some(next) = next {
                required_mode |= self
                    .profile
                    .require_any
                    .iter()
                    .any(|flag| word.split('=').next() == Some(flag.as_str()));
                index = next;
                continue;
            }
            let name = word.split('=').next().unwrap_or(word);
            if self.flags.contains_key(name)
                || !(word.starts_with("--") || (self.profile.single_dash && word.len() > 3))
            {
                return (index, operands, Some(Analysis::Refuse), required_mode);
            }
            let choices = self
                .flags
                .keys()
                .filter(|name| {
                    name.starts_with("--") || (self.profile.single_dash && name.len() > 3)
                })
                .cloned()
                .collect();
            return (
                index,
                operands,
                Some(problem(
                    self.words,
                    index,
                    choices,
                    self.known,
                    self.syntax,
                    true,
                    self.profile.abbreviate,
                )),
                required_mode,
            );
        }
        (index, operands, None, required_mode)
    }
}

pub(crate) fn analyze(
    words: &[String],
    executable: &Path,
    options: &Options<'_>,
    runner: &Runner,
) -> Result<Analysis> {
    let profile = &registry()[&words[0]];
    let text = metadata::help_status(
        executable,
        &profile.help,
        options.cache,
        runner,
        &profile.statuses,
    )?;
    let mut known = advertised(&text);
    if !profile.fresh_commands.is_empty() {
        // Cargo aliases/extensions depend on the current repository and PATH;
        // they must not be reused from another directory's cached help.
        known.extend(advertised(&metadata::capture(
            executable,
            &profile.fresh_commands,
            runner,
        )?));
    }
    let mut flags = evidenced_flags(&profile.flags, &known);
    let mut syntax = vec![words[0].clone()];
    let scanner = Scanner {
        words,
        profile,
        flags: &flags,
        known: &known,
        syntax: &syntax,
    };
    if profile.commands.is_empty() {
        let (_, count, issue, required_mode) = scanner.scan(1, false);
        return Ok(issue.unwrap_or_else(|| {
            let informational = words
                .get(1)
                .is_some_and(|word| matches!(word.as_str(), "--help" | "--version"));
            if (!informational && count < profile.min_operands)
                || count > profile.max_operands
                || !required_mode
            {
                Analysis::Refuse
            } else {
                Analysis::Valid
            }
        }));
    }
    let (index, _, issue, _) = scanner.scan(1, true);
    if let Some(issue) = issue {
        return Ok(issue);
    }
    let Some(command) = words.get(index) else {
        return Ok(Analysis::Refuse);
    };
    let Some(spec) = profile
        .commands
        .get(command)
        .filter(|_| known.contains(command))
    else {
        if !engine::command_word(command) {
            return Ok(Analysis::Refuse);
        }
        let choices = profile
            .commands
            .keys()
            .filter(|name| known.contains(name))
            .cloned()
            .collect();
        return Ok(problem(
            words, index, choices, &known, &syntax, false, false,
        ));
    };
    syntax.push(command.clone());
    if !spec.help.is_empty() {
        // This is a literal reviewed query from the embedded registry, never
        // a route assembled from a user's arguments or an AI response.
        let text = metadata::help_status(
            executable,
            &spec.help,
            options.cache,
            runner,
            &profile.statuses,
        )?;
        known.extend(advertised(&text));
    }
    flags.extend(evidenced_flags(&spec.flags, &known));
    let scanner = Scanner {
        words,
        profile,
        flags: &flags,
        known: &known,
        syntax: &syntax,
    };
    let (_, count, issue, _) = scanner.scan(index + 1, false);
    Ok(issue.unwrap_or({
        if count < spec.min || count > spec.max {
            Analysis::Refuse
        } else {
            Analysis::Valid
        }
    }))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn registry_has_only_unique_linux_executables_and_explicit_help_queries() {
        assert!(registry().len() > 50);
        for (root, profile) in registry() {
            assert!(
                root.as_bytes()
                    .first()
                    .is_some_and(u8::is_ascii_alphanumeric)
                    && root
                        .bytes()
                        .all(|c| c.is_ascii_alphanumeric() || b"._+-".contains(&c)),
                "invalid executable name: {root}"
            );
            assert!(
                !["brew", "winget", "scoop", "choco", "powershell", "pwsh"]
                    .contains(&root.as_str())
            );
            assert!(!profile.help.is_empty(), "{root}");
            assert!(
                !profile.flags.is_empty() || !profile.commands.is_empty(),
                "{root}"
            );
            assert_eq!(
                declared(&profile.flags).len(),
                profile.flags.split_whitespace().count(),
                "duplicate flag in {root}"
            );
            for spec in profile.commands.values() {
                assert!(spec.min <= spec.max);
            }
        }
    }
}
