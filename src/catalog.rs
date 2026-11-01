//! Read-only command discovery and a versioned JSON metadata cache.

use std::collections::BTreeMap;
use std::env;
use std::fs;
use std::os::unix::fs::{DirBuilderExt, MetadataExt, PermissionsExt};
use std::path::Path;
use std::time::{SystemTime, UNIX_EPOCH};

use anyhow::{Result, ensure};
use regex::Regex;
use serde::{Deserialize, Serialize};

use crate::process::Runner;

#[derive(Clone, Debug, Deserialize, Serialize)]
pub(crate) struct Entry {
    pub argv: Vec<String>,
    pub summary: String,
    pub args: String,
    pub source: String,
}

// The tuple matches the existing on-disk JSON format [path, mtime_ns, size].
type Fingerprints = BTreeMap<String, (String, i64, u64)>;

#[derive(Deserialize, Serialize)]
pub(crate) struct Catalog {
    pub version: u32,
    pub binaries: Fingerprints,
    pub created: f64,
    pub entries: Vec<Entry>,
}

#[derive(Deserialize)]
struct OmarchyOutput {
    commands: Vec<OmarchyCommand>,
}

#[derive(Deserialize)]
struct OmarchyCommand {
    route: String,
    summary: String,
    #[serde(default)]
    args: String,
    routes: Option<Vec<String>>,
}

fn now() -> Result<f64> {
    Ok(SystemTime::now().duration_since(UNIX_EPOCH)?.as_secs_f64())
}

pub(crate) fn create_cache(path: &Path) -> Result<()> {
    fs::DirBuilder::new()
        .recursive(true)
        .mode(0o700)
        .create(path)?;
    Ok(())
}

fn fingerprints() -> Fingerprints {
    let mut result = BTreeMap::new();
    let path = env::var_os("PATH").unwrap_or_default();
    for app in ["herdr", "omarchy"] {
        for directory in env::split_paths(&path) {
            let executable = directory.join(app);
            if let Ok(metadata) = fs::metadata(&executable)
                && metadata.is_file()
                && metadata.permissions().mode() & 0o111 != 0
            {
                let nanos = metadata.mtime() * 1_000_000_000 + metadata.mtime_nsec();
                result.insert(
                    app.to_owned(),
                    (
                        executable.to_string_lossy().into_owned(),
                        nanos,
                        metadata.len(),
                    ),
                );
                break;
            }
        }
    }
    result
}

fn clean(text: &str) -> String {
    text.chars()
        .map(|c| {
            if c <= '\u{1f}' || c == '\u{7f}' {
                ' '
            } else {
                c
            }
        })
        .take(240)
        .collect()
}

fn insert(entries: &mut Vec<Entry>, item: Entry) {
    if let Some(existing) = entries.iter_mut().find(|e| e.argv == item.argv) {
        *existing = item;
    } else {
        entries.push(item);
    }
}

fn discover(runner: &Runner, binaries: Fingerprints) -> Result<Catalog> {
    let mut entries = Vec::new();
    if let Some((path, _, _)) = binaries.get("omarchy") {
        let output: OmarchyOutput =
            serde_json::from_str(&runner.capture(path, &["commands", "--json"])?)?;
        for row in output.commands {
            for route in row.routes.unwrap_or_else(|| vec![row.route]) {
                insert(
                    &mut entries,
                    Entry {
                        argv: route.split_whitespace().map(str::to_owned).collect(),
                        summary: clean(&row.summary),
                        args: row.args.clone(),
                        source: "omarchy commands --json".to_owned(),
                    },
                );
            }
        }
    }
    if let Some((path, _, _)) = binaries.get("herdr") {
        let output = runner.capture(path, &["--help"])?;
        let pattern = Regex::new(r"^  (herdr(?:\s+\S+).*?)\s{2,}(\S.*)$")?;
        for line in output.lines() {
            if let Some(captures) = pattern.captures(line) {
                let parts: Vec<&str> = captures[1].split_whitespace().collect();
                let count = parts
                    .iter()
                    .take_while(|word| crate::engine::command_word(word))
                    .count();
                if count > 1 {
                    insert(
                        &mut entries,
                        Entry {
                            argv: parts[..count].iter().map(|s| (*s).to_owned()).collect(),
                            summary: clean(&captures[2]),
                            args: parts[count..].join(" "),
                            source: "herdr --help".to_owned(),
                        },
                    );
                }
            }
        }
        let output = runner.capture(path, &["server", "--help"])?;
        let pattern = Regex::new(r"^  ([a-z][a-z0-9-]*)\s{2,}(\S.*)$")?;
        for line in output.lines() {
            if let Some(captures) = pattern.captures(line) {
                insert(
                    &mut entries,
                    Entry {
                        argv: vec![
                            "herdr".to_owned(),
                            "server".to_owned(),
                            captures[1].to_owned(),
                        ],
                        summary: clean(&captures[2]),
                        args: String::new(),
                        source: "herdr server --help".to_owned(),
                    },
                );
            }
        }
    }
    Ok(Catalog {
        version: 1,
        binaries,
        created: now()?,
        entries,
    })
}

pub(crate) fn load(path: &Path, refresh: bool, runner: &Runner) -> Result<Catalog> {
    let file = path.join("catalog.json");
    let binaries = fingerprints();
    if !refresh
        && let Ok(contents) = fs::read_to_string(&file)
        && let Ok(data) = serde_json::from_str::<Catalog>(&contents)
        && data.version == 1
        && data.binaries == binaries
        && now()? - data.created < 3600.0
    {
        ensure!(
            data.entries.iter().all(|e| !e.argv.is_empty()),
            "empty command route in cache"
        );
        return Ok(data);
    }
    let data = discover(runner, binaries)?;
    create_cache(path)?;
    let mut temporary = tempfile::NamedTempFile::new_in(path)?;
    serde_json::to_writer(&mut temporary, &data)?;
    temporary.persist(file)?;
    Ok(data)
}
