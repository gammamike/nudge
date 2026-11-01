//! Nudge's Linux/Bash prototype, ported without invoking Python at runtime.

#[cfg(not(target_os = "linux"))]
compile_error!("Nudge currently supports Linux only");

mod ai;
mod catalog;
mod claude;
mod cli_adapters;
mod cli_metadata;
mod cli_nested;
mod cli_profiles;
mod codex;
mod config;
mod engine;
mod local;
mod process;
mod shell_words;
mod terminal;

use std::env;
use std::path::PathBuf;
use std::process::ExitCode;
use std::sync::Arc;
use std::sync::atomic::{AtomicBool, Ordering};
use std::time::{Duration, Instant};

use anyhow::{Context, Result, bail, ensure};
use serde_json::json;
use signal_hook::consts::signal::{SIGHUP, SIGINT, SIGTERM};

use crate::ai::Provider;
use crate::engine::Options;
use crate::process::Runner;

fn execute(runner: &Runner) -> Result<()> {
    let mut args = env::args().skip(1);
    let action = args.next().unwrap_or_else(|| "--help".to_owned());
    if action == "supported" {
        for root in [
            "herdr",
            "omarchy",
            "git",
            "docker",
            "systemctl",
            "journalctl",
        ] {
            println!("{root}");
        }
        for root in cli_profiles::roots().chain(cli_nested::roots()) {
            println!("{root}");
        }
        return Ok(());
    }
    if matches!(action.as_str(), "--help" | "-h") {
        println!(
            "nudge-rust <refresh|suggest|confirm|config|models|supported> [--command TEXT] [--status CODE] [--local-only] [--provider codex|claude|ollama|local] [--model ID] [--endpoint URL] [--force-ai]\nconfig: show effective settings, or save supplied provider/model/endpoint.\nmodels: list models from the selected local server.\nsupported: list registered Linux executable adapters; see docs for each adapter's scope. Settings precedence: flags > environment > config > defaults."
        );
        return Ok(());
    }
    ensure!(
        ["refresh", "suggest", "confirm", "config", "models"].contains(&action.as_str()),
        "unknown action"
    );
    let cache = env::var_os("NUDGE_CACHE_DIR")
        .map(PathBuf::from)
        .unwrap_or_else(|| PathBuf::from(env!("CARGO_MANIFEST_DIR")).join(".cache"));
    let config_path = config::path()?;
    let mut saved = config::Config::load(&config_path)?;
    let mut provider_override = None;
    let mut model_override = None;
    let mut endpoint_override = None;
    let mut status = 1;
    let mut local_only = env::var("NUDGE_LOCAL_ONLY").is_ok_and(|value| value == "1");
    let mut force_ai = false;
    let mut force_codex = false;
    let mut line = String::new();
    while let Some(arg) = args.next() {
        match arg.as_str() {
            "--command" => line = args.next().context("missing --command value")?,
            "--status" => status = args.next().context("missing --status value")?.parse()?,
            "--local-only" => local_only = true,
            "--provider" => {
                provider_override = Some(Provider::parse(
                    &args.next().context("missing --provider value")?,
                )?)
            }
            "--model" => model_override = Some(args.next().context("missing --model value")?),
            "--endpoint" => {
                endpoint_override = Some(args.next().context("missing --endpoint value")?)
            }
            "--force-ai" => force_ai = true,
            "--force-codex" => {
                force_ai = true;
                force_codex = true;
            }
            _ => bail!("unknown option: {arg}"),
        }
    }
    let provider = if let Some(provider) = provider_override {
        provider
    } else {
        Provider::parse(
            &env::var("NUDGE_PROVIDER")
                .ok()
                .or_else(|| saved.provider.clone())
                .unwrap_or_else(|| "codex".to_owned()),
        )?
    };
    ensure!(
        !force_codex || provider == Provider::Codex,
        "--force-codex requires the codex provider; use --force-ai for other providers"
    );
    if let Some(model) = &model_override {
        config::validate_model(model)?;
    }
    if let Some(endpoint) = &endpoint_override {
        ensure!(provider.is_local(), "--endpoint requires a local provider");
        local::endpoint(endpoint)?;
    }
    if action == "config"
        && (provider_override.is_some() || model_override.is_some() || endpoint_override.is_some())
    {
        if provider_override.is_some() {
            saved.provider = Some(provider.key().to_owned());
        }
        if let Some(model) = &model_override {
            saved
                .models
                .insert(provider.key().to_owned(), model.clone());
        }
        if let Some(endpoint) = &endpoint_override {
            saved
                .endpoints
                .insert(provider.key().to_owned(), endpoint.clone());
        }
        saved.save(&config_path)?;
        println!(
            "{}",
            json!({"saved_to": config_path, "config": saved,
            "note": "Environment variables and command flags override saved settings."})
        );
        return Ok(());
    }
    let model = model_override.unwrap_or_else(|| saved.model(provider));
    if !model.is_empty() {
        config::validate_model(&model)?;
    }
    let endpoint = endpoint_override.unwrap_or_else(|| saved.endpoint(provider));
    if action == "config" {
        println!(
            "{}",
            json!({"path": config_path, "provider": provider.key(), "model": model,
            "endpoint": endpoint, "config": saved})
        );
        return Ok(());
    }
    let legacy_timeout = format!("NUDGE_{}_TIMEOUT", provider.key().to_ascii_uppercase());
    let seconds: f64 = env::var("NUDGE_AI_TIMEOUT")
        .or_else(|_| env::var(legacy_timeout))
        .unwrap_or_else(|_| "15".to_owned())
        .parse()?;
    ensure!(
        seconds.is_finite() && seconds > 0.0,
        "timeout must be positive and finite"
    );
    let options = Options {
        cache: &cache,
        status,
        local_only,
        force_ai,
        provider,
        announce: action == "confirm",
        model: &model,
        endpoint: &endpoint,
        timeout: Duration::try_from_secs_f64(seconds)?,
    };
    if action == "models" {
        let models = local::models(provider, &endpoint, options.timeout, runner)?;
        println!("{}", json!({"provider": provider.key(), "models": models}));
        return Ok(());
    }
    if action == "refresh" {
        let started = Instant::now();
        let data = catalog::load(&cache, true, runner)?;
        println!(
            "{}",
            json!({"commands": data.entries.len(), "elapsed_ms": started.elapsed().as_secs_f64() * 1000.0})
        );
        return Ok(());
    }
    let result = engine::suggest(&line, &options, runner)?;
    if action == "confirm" {
        terminal::confirm(&result, runner)?;
    } else {
        println!("{}", serde_json::to_string_pretty(&result)?);
    }
    Ok(())
}

fn main() -> ExitCode {
    let interrupted = Arc::new(AtomicBool::new(false));
    for signal in [SIGINT, SIGTERM, SIGHUP] {
        if let Err(error) = signal_hook::flag::register(signal, Arc::clone(&interrupted)) {
            eprintln!("nudge: cannot register signal handler: {error}");
            return ExitCode::FAILURE;
        }
    }
    let runner = Runner {
        interrupted: Arc::clone(&interrupted),
    };
    let result = execute(&runner);
    if interrupted.load(Ordering::Relaxed) {
        return ExitCode::from(130);
    }
    match result {
        Ok(()) => ExitCode::SUCCESS,
        Err(error) => {
            eprintln!("nudge: {error}; returning to shell");
            ExitCode::FAILURE
        }
    }
}
