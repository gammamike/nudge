//! Persist provider-specific choices without hard-coding available model IDs.

use std::collections::BTreeMap;
use std::env;
use std::fs;
use std::io::{ErrorKind, Write};
use std::path::{Path, PathBuf};

use anyhow::{Context, Result, ensure};
use serde::{Deserialize, Serialize};

use crate::ai::Provider;

#[derive(Default, Deserialize, Serialize)]
#[serde(default, deny_unknown_fields)]
pub(crate) struct Config {
    pub provider: Option<String>,
    pub models: BTreeMap<String, String>,
    pub endpoints: BTreeMap<String, String>,
}

pub(crate) fn path() -> Result<PathBuf> {
    if let Some(path) = env::var_os("NUDGE_CONFIG") {
        return Ok(PathBuf::from(path));
    }
    let directory = env::var_os("XDG_CONFIG_HOME")
        .filter(|value| !value.is_empty())
        .map(PathBuf::from)
        .or_else(|| env::var_os("HOME").map(|value| PathBuf::from(value).join(".config")))
        .context("HOME or XDG_CONFIG_HOME must be set, or use NUDGE_CONFIG")?;
    Ok(directory.join("nudge/config.json"))
}

pub(crate) fn validate_model(value: &str) -> Result<()> {
    ensure!(
        !value.is_empty()
            && value.len() <= 256
            && !value.starts_with('-')
            && value
                .bytes()
                .all(|byte| byte.is_ascii_alphanumeric() || b"-_.:/[]".contains(&byte)),
        "invalid model identifier"
    );
    Ok(())
}

impl Config {
    pub fn load(path: &Path) -> Result<Self> {
        let data = match fs::read(path) {
            Ok(data) => data,
            Err(error) if error.kind() == ErrorKind::NotFound => return Ok(Self::default()),
            Err(error) => return Err(error).context("cannot read Nudge configuration"),
        };
        let config: Self =
            serde_json::from_slice(&data).context("invalid Nudge configuration JSON")?;
        if let Some(provider) = &config.provider {
            Provider::parse(provider)?;
        }
        for (provider, model) in &config.models {
            Provider::parse(provider)?;
            validate_model(model)?;
        }
        for provider in config.endpoints.keys() {
            ensure!(
                Provider::parse(provider)?.is_local(),
                "endpoints require a local provider"
            );
        }
        Ok(config)
    }

    pub fn save(&self, path: &Path) -> Result<()> {
        let parent = path
            .parent()
            .filter(|p| !p.as_os_str().is_empty())
            .unwrap_or(Path::new("."));
        fs::create_dir_all(parent)?;
        let mut file = tempfile::NamedTempFile::new_in(parent)?;
        serde_json::to_writer_pretty(&mut file, self)?;
        writeln!(file)?;
        file.as_file().sync_all()?;
        file.persist(path)?;
        Ok(())
    }

    pub fn model(&self, provider: Provider) -> String {
        let key = format!("NUDGE_{}_MODEL", provider.key().to_ascii_uppercase());
        env::var(key)
            .ok()
            .or_else(|| {
                (provider == Provider::Codex)
                    .then(|| env::var("NUDGE_MODEL").ok())
                    .flatten()
            })
            .or_else(|| self.models.get(provider.key()).cloned())
            .unwrap_or_else(|| match provider {
                Provider::Codex => "gpt-6-luna".to_owned(),
                Provider::Claude => "haiku".to_owned(),
                Provider::Ollama | Provider::Local => String::new(),
            })
    }

    pub fn endpoint(&self, provider: Provider) -> String {
        let key = format!("NUDGE_{}_URL", provider.key().to_ascii_uppercase());
        env::var(key)
            .ok()
            .or_else(|| self.endpoints.get(provider.key()).cloned())
            .unwrap_or_else(|| match provider {
                Provider::Ollama => "http://127.0.0.1:11434".to_owned(),
                Provider::Local => "http://127.0.0.1:1234/v1".to_owned(),
                _ => String::new(),
            })
    }
}
