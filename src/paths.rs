//! Per-user directories shared by installed and source-checkout execution.

use std::env;
use std::path::PathBuf;

use anyhow::{Context, Result, ensure};

pub(crate) fn home() -> Result<PathBuf> {
    let path = env::var_os("HOME")
        .map(PathBuf::from)
        .context("HOME must be set")?;
    ensure!(path.is_absolute(), "HOME must be an absolute path");
    Ok(path)
}

pub(crate) fn xdg(name: &str, fallback: &str) -> Result<PathBuf> {
    if let Some(path) = env::var_os(name)
        .map(PathBuf::from)
        .filter(|p| p.is_absolute())
    {
        return Ok(path);
    }
    Ok(home()?.join(fallback))
}

pub(crate) fn cache() -> Result<PathBuf> {
    if let Some(path) = env::var_os("NUDGE_CACHE_DIR").filter(|p| !p.is_empty()) {
        return Ok(path.into());
    }
    Ok(xdg("XDG_CACHE_HOME", ".cache")?.join("nudge"))
}
