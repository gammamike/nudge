//! Explicit model readiness check using synthetic data and the fallback boundary.

use std::time::Instant;

use anyhow::Result;
use serde::Serialize;

use crate::ai::Provider;
use crate::catalog::Entry;
use crate::engine::Options;
use crate::process::Runner;
use crate::{claude, codex, local};

#[derive(Serialize)]
pub(crate) struct Check {
    ok: bool,
    provider: &'static str,
    model: String,
    message: String,
    elapsed_ms: f64,
}

pub(crate) fn run(options: &Options<'_>, runner: &Runner) -> Result<Check> {
    let started = Instant::now();
    // These are fixed test data, not installed commands. Never run discovery,
    // read history, or execute a command to test a provider connection.
    let words = vec!["nudge-probe".to_owned(), "chekc".to_owned()];
    let entry = Entry {
        argv: vec!["nudge-probe".to_owned(), "check".to_owned()],
        summary: "Synthetic connection test: correct the typo chekc to check".to_owned(),
        args: String::new(),
        source: "connection test".to_owned(),
    };
    let choices = [&entry];
    let result = match options.provider {
        Provider::Codex => codex::pick(&words, &choices, options, runner),
        Provider::Claude => claude::pick(&words, &choices, options, runner),
        Provider::Ollama | Provider::Local => local::pick(&words, &choices, options, runner),
    };
    runner.check_interrupt()?;
    let (ok, message) = match result {
        Ok((Some(_), _)) => (true, "Connected — model test passed".to_owned()),
        Ok((None, reason)) => (
            false,
            reason.unwrap_or_else(|| "Model test failed".to_owned()),
        ),
        Err(error) => (false, error.to_string()),
    };
    Ok(Check {
        ok,
        provider: options.provider.key(),
        model: options.model.to_owned(),
        message,
        elapsed_ms: started.elapsed().as_secs_f64() * 1000.0,
    })
}
