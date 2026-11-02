//! Subscription-authenticated Codex selection; never executes a correction.

use std::env;
use std::fs::{self, File};
use std::process::{Command, Stdio};
use std::time::Duration;

use anyhow::Result;
use serde_json::Value;

use crate::ai;
use crate::catalog::{self, Entry};
use crate::engine::{self, Options};
use crate::process::Runner;

fn command() -> Command {
    let mut command = Command::new("codex");
    for (key, _) in env::vars_os() {
        let name = key.to_string_lossy();
        if [
            "OPENAI_API_KEY",
            "CODEX_API_KEY",
            "OPENAI_BASE_URL",
            "OPENAI_ORG_ID",
            "OPENAI_PROJECT_ID",
            "CODEX_THREAD_ID",
            "CODEX_INTERNAL_ORIGINATOR_OVERRIDE",
        ]
        .contains(&name.as_ref())
            || name.starts_with("CODEX_APP_SERVER")
        {
            command.env_remove(key);
        }
    }
    command
}

pub(crate) fn pick<'a>(
    words: &[String],
    choices: &[&'a Entry],
    options: &Options<'_>,
    runner: &Runner,
) -> Result<(Option<&'a Entry>, Option<String>)> {
    let auth = match runner.run(
        command().args(["login", "status"]).stdin(Stdio::null()),
        Duration::from_secs(4),
    ) {
        Ok(auth) => auth,
        Err(_) => {
            runner.check_interrupt()?;
            return Ok((
                None,
                Some(
                    "Codex authentication check failed; check CLI installation and login"
                        .to_owned(),
                ),
            ));
        }
    };
    if !auth.status.success()
        || !format!("{}{}", auth.stdout, auth.stderr).contains("Logged in using ChatGPT")
    {
        return Ok((
            None,
            Some("Codex needs a ChatGPT login; API billing is disabled".to_owned()),
        ));
    }
    let choices = engine::shortlist(words, choices);
    if choices.is_empty() {
        return Ok((None, Some("no eligible commands".to_owned())));
    }
    let prompt = ai::prompt(words, &choices)?;
    let schema = ai::schema();
    catalog::create_cache(options.cache)?;
    let temporary = tempfile::Builder::new()
        .prefix("codex-")
        .tempdir_in(options.cache)?;
    let path = temporary.path().canonicalize()?;
    fs::write(path.join("schema.json"), serde_json::to_vec(&schema)?)?;
    fs::write(path.join("prompt.txt"), prompt)?;
    let mut invocation = command();
    invocation
        .args([
            "--no-daemon",
            "exec",
            "--ignore-user-config",
            "--ephemeral",
            "--skip-git-repo-check",
            "--sandbox",
            "read-only",
            "--color",
            "never",
            "--model",
            options.model,
        ])
        .arg("-C")
        .arg(&path)
        .arg("--output-schema")
        .arg(path.join("schema.json"))
        .arg("-o")
        .arg(path.join("result.json"))
        .arg("--json");
    for setting in [
        "model_provider=\"openai\"",
        "model_reasoning_effort=\"none\"",
        "approval_policy=\"never\"",
        "web_search=\"disabled\"",
        "project_doc_max_bytes=0",
        "forced_login_method=\"chatgpt\"",
    ] {
        invocation.args(["-c", setting]);
    }
    for feature in [
        "shell_tool",
        "apps",
        "plugins",
        "hooks",
        "multi_agent",
        "browser_use",
        "computer_use",
        "image_generation",
        "shell_snapshot",
    ] {
        invocation.args(["--disable", feature]);
    }
    invocation
        .args(["--enable", "skip_host_skill_discovery", "-"])
        .stdin(File::open(path.join("prompt.txt"))?);
    let output = match runner.run(&mut invocation, options.timeout) {
        Ok(output) => output,
        Err(error) => {
            runner.check_interrupt()?;
            let reason = if error.to_string().contains("timed out") {
                format!("Codex timed out after {}s", options.timeout.as_secs_f64())
            } else {
                "Codex returned an invalid response; no correction suggested".to_owned()
            };
            return Ok((None, Some(reason)));
        }
    };
    if !output.status.success() {
        return Ok((
            None,
            Some(format!(
                "Codex exited {}; no correction",
                output.status.code().unwrap_or(-1)
            )),
        ));
    }
    let parsed = fs::read(path.join("result.json"))
        .ok()
        .and_then(|bytes| serde_json::from_slice::<Value>(&bytes).ok());
    let Some(parsed) = parsed else {
        return Ok((
            None,
            Some("Codex returned an invalid response; no correction suggested".to_owned()),
        ));
    };
    Ok(ai::selection_result(&parsed, &choices, options.provider))
}
