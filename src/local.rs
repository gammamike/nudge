//! Loopback-only Ollama and OpenAI-compatible model servers.

use std::io::{Seek, SeekFrom, Write};
use std::net::SocketAddr;
use std::process::{Command, Stdio};
use std::time::{Duration, Instant};

use anyhow::{Context, Result, ensure};
use serde_json::{Value, json};

use crate::ai::{self, Provider};
use crate::catalog::Entry;
use crate::engine::{self, Options};
use crate::process::Runner;

// Accept a deliberately narrow URL grammar: loopback HTTP, explicit port, and
// an optional literal base path. Normalize localhost without a DNS lookup.
pub(crate) fn endpoint(value: &str) -> Result<String> {
    let rest = value
        .strip_prefix("http://")
        .context("local endpoint must use http://")?;
    let (authority, path) = rest.split_once('/').unwrap_or((rest, ""));
    let address: SocketAddr = if let Some(port) = authority.strip_prefix("localhost:") {
        format!("127.0.0.1:{port}").parse()?
    } else {
        authority
            .parse()
            .context("local endpoint needs a loopback IP and explicit port")?
    };
    ensure!(
        address.ip().is_loopback() && address.port() != 0,
        "local endpoint must be loopback with a nonzero port"
    );
    ensure!(
        path.bytes()
            .all(|b| b.is_ascii_alphanumeric() || b"/-_".contains(&b)),
        "invalid endpoint base path"
    );
    let path = path.trim_end_matches('/');
    Ok(if path.is_empty() {
        format!("http://{address}")
    } else {
        format!("http://{address}/{path}")
    })
}

fn request(
    base: &str,
    route: &str,
    body: Option<&Value>,
    timeout: Duration,
    runner: &Runner,
) -> Result<Value> {
    let url = format!("{}{route}", endpoint(base)?);
    // curl avoids a resident HTTP runtime and reuses the same cancellable
    // subprocess runner as the subscription CLIs. Ignore curlrc, proxies,
    // redirects and credentials so this remains a loopback-only transport.
    let mut command = Command::new("curl");
    command.args([
        "--disable",
        "--silent",
        "--show-error",
        "--fail",
        "--globoff",
        "--proxy",
        "",
        "--noproxy",
        "*",
        "--proto",
        "=http",
        "--connect-timeout",
        "2",
        "--max-time",
        &timeout.as_secs_f64().to_string(),
        "--max-filesize",
        "1048576",
        "--header",
        "Content-Type: application/json",
        "--url",
        &url,
    ]);
    let mut input = tempfile::tempfile()?;
    if let Some(body) = body {
        serde_json::to_writer(&mut input, body)?;
        input.flush()?;
        input.seek(SeekFrom::Start(0))?;
        command.args(["--data-binary", "@-"]).stdin(input);
    } else {
        command.stdin(Stdio::null());
    }
    let response = runner.run(&mut command, timeout)?;
    ensure!(
        response.status.success(),
        "local model HTTP request failed (curl exit {}); check server, model, and timeout",
        response.status.code().unwrap_or(-1)
    );
    let parsed: Value =
        serde_json::from_str(&response.stdout).context("local server returned invalid JSON")?;
    ensure!(
        parsed.get("error").is_none(),
        "local server returned an error"
    );
    Ok(parsed)
}

fn remote(value: &Value) -> bool {
    ["remote_host", "remote_model"].iter().any(|key| {
        value
            .get(key)
            .is_some_and(|v| !v.is_null() && v.as_str() != Some(""))
    })
}

pub(crate) fn models(
    provider: Provider,
    base: &str,
    timeout: Duration,
    runner: &Runner,
) -> Result<Vec<String>> {
    ensure!(
        provider.is_local(),
        "model discovery is available for ollama/local; use the provider CLI's model picker for subscription availability"
    );
    let (route, field, name) = match provider {
        Provider::Ollama => ("/api/tags", "models", "name"),
        _ => ("/models", "data", "id"),
    };
    let response = request(base, route, None, timeout, runner)?;
    let entries = response[field]
        .as_array()
        .context("invalid model listing")?;
    let mut names: Vec<String> = entries
        .iter()
        .filter(|entry| !remote(entry))
        .filter_map(|entry| entry[name].as_str().map(str::to_owned))
        .collect();
    names.sort();
    names.dedup();
    Ok(names)
}

fn completion(
    words: &[String],
    choices: &[&Entry],
    options: &Options<'_>,
    runner: &Runner,
) -> Result<Value> {
    ensure!(
        !options.model.is_empty(),
        "choose an installed model using --model or config --model; use models to list local models"
    );
    let started = Instant::now();
    if options.provider == Provider::Ollama {
        let info = request(
            options.endpoint,
            "/api/show",
            Some(&json!({"model": options.model})),
            options.timeout,
            runner,
        )?;
        ensure!(
            !remote(&info),
            "Ollama cloud/remote models are not supported by the local provider"
        );
        ensure!(
            info["model_info"].is_object(),
            "Ollama did not identify a local model"
        );
    }
    let messages = json!([
        {"role": "system", "content": "Select a listed command candidate or decline. Return JSON with only candidate_id. Never execute commands or use tools."},
        {"role": "user", "content": ai::prompt(words, choices)?}
    ]);
    let (route, body) = match options.provider {
        Provider::Ollama => (
            "/api/chat",
            json!({
                "model": options.model, "messages": messages, "stream": false,
                "format": ai::schema(), "think": false, "keep_alive": "5m",
                "options": {"temperature": 0, "num_predict": 128}
            }),
        ),
        _ => (
            "/chat/completions",
            json!({
                "model": options.model, "messages": messages, "stream": false,
                "temperature": 0, "max_tokens": 128,
                "response_format": {"type": "json_schema", "json_schema": {
                    "name": "command_selection", "strict": true, "schema": ai::schema()
                }}
            }),
        ),
    };
    let remaining = options
        .timeout
        .checked_sub(started.elapsed())
        .context("local model request timed out")?;
    let response = request(options.endpoint, route, Some(&body), remaining, runner)?;
    let message = if options.provider == Provider::Ollama {
        ensure!(
            !remote(&response) && response["done"] == true && response["done_reason"] == "stop",
            "incomplete or remote Ollama response"
        );
        &response["message"]
    } else {
        let choices = response["choices"]
            .as_array()
            .context("missing local response choices")?;
        ensure!(
            choices.len() == 1 && choices[0]["finish_reason"] == "stop",
            "incomplete local response"
        );
        &choices[0]["message"]
    };
    ensure!(
        message["role"] == "assistant",
        "invalid local response role"
    );
    ensure!(
        message
            .get("tool_calls")
            .is_none_or(|v| v.is_null() || v.as_array().is_some_and(Vec::is_empty)),
        "local model attempted tool use"
    );
    let content = message["content"]
        .as_str()
        .context("missing local response content")?;
    serde_json::from_str(content).context("local model returned invalid selection JSON")
}

pub(crate) fn pick<'a>(
    words: &[String],
    choices: &[&'a Entry],
    options: &Options<'_>,
    runner: &Runner,
) -> Result<(Option<&'a Entry>, Option<String>)> {
    let choices = engine::shortlist(words, choices);
    if choices.is_empty() {
        return Ok((None, Some("no eligible commands".to_owned())));
    }
    match completion(words, &choices, options, runner) {
        Ok(value) => match ai::selected(&value, &choices) {
            Some(entry) => Ok((Some(entry), None)),
            None => Ok((
                None,
                Some("local model declined or returned an invalid selection".to_owned()),
            )),
        },
        Err(error) => {
            runner.check_interrupt()?;
            Ok((None, Some(error.to_string())))
        }
    }
}

#[cfg(test)]
mod tests {
    use super::endpoint;

    #[test]
    fn loopback_urls_only() {
        assert_eq!(
            endpoint("http://localhost:1234/v1/").unwrap(),
            "http://127.0.0.1:1234/v1"
        );
        assert!(endpoint("http://[::1]:8080/v1").is_ok());
        for url in [
            "https://localhost:1234",
            "http://example.com:1234",
            "http://127.0.0.1:0",
            "http://127.0.0.1",
            "http://user@127.0.0.1:1",
            "http://127.0.0.1:1/v1?x=y",
            "http://127.0.0.1:1/../v1",
            "http://10.0.0.1:1234",
        ] {
            assert!(endpoint(url).is_err(), "{url}");
        }
    }
}
