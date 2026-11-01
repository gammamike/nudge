//! Local corrections and Python-compatible candidate ranking.

use std::collections::HashSet;
use std::path::Path;
use std::time::{Duration, Instant};

use anyhow::Result;
use serde::Serialize;

use crate::ai::Provider;
use crate::catalog::{self, Catalog, Entry};
use crate::claude;
use crate::codex;
use crate::local;
use crate::process::Runner;
use crate::terminal;

const EXCLUDED: &[&str] = &[
    "shutdown",
    "reboot",
    "reset",
    "reset-keys",
    "remove",
    "delete",
    "reinstall",
    "refresh",
    "wipe",
    "format",
];

#[derive(Serialize)]
pub(crate) struct Suggestion {
    pub command: String,
    pub suggestion: Option<String>,
    pub source: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub reason: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub argv: Option<Vec<String>>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub executable: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub evidence: Option<String>,
    pub elapsed_ms: f64,
}

pub(crate) struct Options<'a> {
    pub cache: &'a Path,
    pub status: i32,
    pub local_only: bool,
    pub force_ai: bool,
    pub provider: Provider,
    pub announce: bool,
    pub model: &'a str,
    pub endpoint: &'a str,
    pub timeout: Duration,
}

pub(crate) fn command_word(word: &str) -> bool {
    word.as_bytes().first().is_some_and(u8::is_ascii_lowercase)
        && word
            .bytes()
            .all(|b| b.is_ascii_lowercase() || b.is_ascii_digit() || b == b'-')
}

fn parse(line: &str) -> Option<Vec<String>> {
    if line.starts_with(' ') || line.ends_with(' ') {
        return None;
    }
    let words: Vec<String> = line
        .split(' ')
        .filter(|s| !s.is_empty())
        .map(str::to_owned)
        .collect();
    if !(2..=6).contains(&words.len())
        || !words.iter().all(|w| command_word(w))
        || !["herdr", "omarchy"].contains(&words[0].as_str())
    {
        return None;
    }
    Some(words)
}

pub(crate) fn typo(a: &str, b: &str) -> usize {
    if a == b {
        return 0;
    }
    let a: Vec<char> = a.chars().collect();
    let b: Vec<char> = b.chars().collect();
    if a.len().min(b.len()) < 3 {
        return 99;
    }
    if a.len() == b.len() {
        let differences: Vec<usize> = (0..a.len()).filter(|&i| a[i] != b[i]).collect();
        match differences.as_slice() {
            [_] => return 1,
            [i, j] if *j == *i + 1 && a[*i] == b[*j] && a[*j] == b[*i] => return 1,
            _ => {}
        }
    }
    if a.len().abs_diff(b.len()) == 1 {
        let (long, short) = if a.len() > b.len() {
            (&a, &b)
        } else {
            (&b, &a)
        };
        for i in 0..long.len() {
            if long[..i] == short[..i] && long[i + 1..] == short[i..] {
                return 1;
            }
        }
    }
    99
}

fn distance(words: &[String], target: &[String]) -> usize {
    if words.len() == target.len() {
        return words.iter().zip(target).map(|(a, b)| typo(a, b)).sum();
    }
    if target.len() == words.len() + 1 {
        for i in 1..target.len() {
            if target[..i] == words[..i] && target[i + 1..] == words[i..] {
                return 1;
            }
        }
    }
    99
}

fn optional_only(args: &str) -> bool {
    let mut rest = args;
    while let Some(start) = rest.find('[') {
        if !rest[..start].trim().is_empty() {
            return false;
        }
        let Some(end) = rest[start + 1..].find(']') else {
            return false;
        };
        rest = &rest[start + end + 2..];
    }
    rest.trim().is_empty()
}

pub(crate) fn candidates<'a>(words: &[String], data: &'a Catalog) -> Vec<&'a Entry> {
    data.entries
        .iter()
        .filter(|e| {
            e.argv[0] == words[0]
                && optional_only(&e.args)
                && !e.argv.iter().any(|w| EXCLUDED.contains(&w.as_str()))
                && e.argv.len() >= words.len()
        })
        .collect()
}

fn known(words: &[String], data: &Catalog) -> bool {
    data.entries.iter().any(|entry| {
        let route = &entry.argv;
        route.starts_with(words)
            || (!entry.args.is_empty() && words.starts_with(route))
            || (!entry.args.is_empty()
                && words.len() > route.len()
                && distance(&words[..route.len()], route) <= 1)
    })
}

/// Equivalent to difflib.SequenceMatcher's ratio for short, non-junk strings.
/// Routes are shorter than its 200-character autojunk threshold.
pub(crate) fn similarity(a: &str, b: &str) -> f64 {
    let a: Vec<char> = a.chars().collect();
    let b: Vec<char> = b.chars().collect();
    if a.is_empty() && b.is_empty() {
        return 1.0;
    }
    let mut pending = vec![(0, a.len(), 0, b.len())];
    let mut matched = 0;
    while let Some((a_start, a_end, b_start, b_end)) = pending.pop() {
        let (mut best_i, mut best_j, mut best_len) = (a_start, b_start, 0);
        let mut previous = vec![0; b.len() + 1];
        for (i, a_char) in a.iter().enumerate().take(a_end).skip(a_start) {
            let mut current = vec![0; b.len() + 1];
            for j in b_start..b_end {
                if *a_char == b[j] {
                    current[j + 1] = previous[j] + 1;
                    if current[j + 1] > best_len {
                        best_len = current[j + 1];
                        best_i = i + 1 - best_len;
                        best_j = j + 1 - best_len;
                    }
                }
            }
            previous = current;
        }
        if best_len > 0 {
            matched += best_len;
            if a_start < best_i && b_start < best_j {
                pending.push((a_start, best_i, b_start, best_j));
            }
            if best_i + best_len < a_end && best_j + best_len < b_end {
                pending.push((best_i + best_len, a_end, best_j + best_len, b_end));
            }
        }
    }
    2.0 * matched as f64 / (a.len() + b.len()) as f64
}

pub(crate) fn shortlist<'a>(words: &[String], choices: &[&'a Entry]) -> Vec<&'a Entry> {
    let input = words.join(" ");
    let wanted: HashSet<&String> = words[1..].iter().collect();
    let mut ranked: Vec<_> = choices
        .iter()
        .map(|entry| {
            let available: HashSet<&String> = entry.argv[1..].iter().collect();
            (
                *entry,
                wanted.intersection(&available).count(),
                similarity(&input, &entry.argv.join(" ")),
            )
        })
        .collect();
    // Stable descending sort preserves the Python catalog's order on ties.
    ranked.sort_by(|a, b| b.1.cmp(&a.1).then_with(|| b.2.total_cmp(&a.2)));
    ranked
        .into_iter()
        .take(24)
        .map(|(entry, _, _)| entry)
        .collect()
}

pub(crate) fn suggest(line: &str, options: &Options<'_>, runner: &Runner) -> Result<Suggestion> {
    if line
        .split_whitespace()
        .next()
        .is_some_and(crate::cli_adapters::supports)
    {
        return crate::cli_adapters::suggest(line, options, runner);
    }
    let started = Instant::now();
    let mut result = Suggestion {
        command: line.to_owned(),
        suggestion: None,
        source: "none".to_owned(),
        reason: None,
        argv: None,
        executable: None,
        evidence: None,
        elapsed_ms: 0.0,
    };
    let words = parse(line);
    if matches!(options.status, 0 | 130)
        || words.is_none()
        || words
            .as_ref()
            .is_some_and(|v| v.iter().any(|w| EXCLUDED.contains(&w.as_str())))
    {
        result.reason = Some("outside prototype scope or no actionable failure".to_owned());
    } else if let Some(words) = words {
        let data = catalog::load(options.cache, false, runner)?;
        if known(&words, &data) && !options.force_ai {
            result.reason = Some("known command syntax; no speculative retry".to_owned());
        } else {
            let choices = candidates(&words, &data);
            let matches: Vec<_> = choices
                .iter()
                .filter(|entry| distance(&words, &entry.argv) == 1)
                .collect();
            let selected = if matches.len() == 1 && !options.force_ai {
                result.source = "local".to_owned();
                Some(*matches[0])
            } else if options.local_only {
                result.reason = Some("ambiguous or no local match".to_owned());
                None
            } else {
                if options.announce {
                    terminal::announce(options.provider)?;
                }
                let (selected, reason) = match options.provider {
                    Provider::Codex => codex::pick(&words, &choices, options, runner)?,
                    Provider::Claude => claude::pick(&words, &choices, options, runner)?,
                    Provider::Ollama | Provider::Local => {
                        local::pick(&words, &choices, options, runner)?
                    }
                };
                result.source = options.provider.name().to_owned();
                result.reason = reason;
                selected
            };
            if let Some(entry) = selected {
                result.suggestion = Some(entry.argv.join(" "));
                result.argv = Some(entry.argv.clone());
                result.executable = data.binaries.get(&words[0]).map(|b| b.0.clone());
                result.evidence = Some(entry.source.clone());
            }
        }
    }
    result.elapsed_ms = (started.elapsed().as_secs_f64() * 100_000.0).round() / 100.0;
    Ok(result)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn literal_input_only() {
        for line in ["herdr stop", "omarchy  theme list"] {
            assert!(parse(line).is_some());
        }
        for line in [
            "herdr stop; id",
            "herdr $(id)",
            "herdr stop\n",
            "herdr\tstop",
            " herdr stop",
            "herdr --help",
            "sudo herdr stop",
        ] {
            assert!(parse(line).is_none(), "accepted unsupported input: {line}");
        }
    }

    #[test]
    fn one_edit_and_optional_arguments() {
        for (a, b) in [
            ("lsit", "list"),
            ("terminl", "terminal"),
            ("themes", "theme"),
            ("stop", "stup"),
        ] {
            assert_eq!(typo(a, b), 1);
        }
        assert_eq!(typo("halt", "stop"), 99);
        assert!(optional_only("[--status] [--json]"));
        assert!(!optional_only("<name> [--json]"));
    }

    #[test]
    fn sequence_matcher_tie_behavior() {
        assert_eq!(similarity("tide", "diet"), 0.25);
        assert_eq!(similarity("diet", "tide"), 0.5);
        assert_eq!(similarity("abcd", "bcde"), 0.75);
    }
}
