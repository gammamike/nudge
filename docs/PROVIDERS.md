# Provider configuration

Local matching runs first. When it cannot select a correction, a configured
provider can choose one of the eligible command routes or decline. It cannot
supply arbitrary executable code. Every suggestion still requires confirmation.

## Settings

```bash
./target/release/nudge-rust config
./target/release/nudge-rust config --provider claude --model haiku
```

Settings are saved atomically in `~/.config/nudge/config.json`, respecting
`XDG_CONFIG_HOME` or `NUDGE_CONFIG`. The file is created with mode 0600. Models are
remembered independently for each provider. Reading settings does not create a
file. Use an alias or full model ID available to your account or server.

Precedence: command-line options, environment variables, saved configuration,
then defaults. An exported environment setting overrides a saved setting.

| Setting | Behavior |
|---|---|
| `NUDGE_ENABLED` | Set to `0` to disable the Bash hook |
| `NUDGE_LOCAL_ONLY` | Set to `1` to disable every model provider, including local models |
| `NUDGE_PROVIDER` | `codex` (default), `claude`, `ollama`, or `local` |
| `NUDGE_CODEX_MODEL` | Default `gpt-6-luna`; legacy `NUDGE_MODEL` also supported |
| `NUDGE_CLAUDE_MODEL` | Default `haiku` |
| `NUDGE_OLLAMA_MODEL`, `NUDGE_LOCAL_MODEL` | No default; choose a model installed on your server |
| `NUDGE_OLLAMA_URL` | Default `http://127.0.0.1:11434` |
| `NUDGE_LOCAL_URL` | Default `http://127.0.0.1:1234/v1` |
| `NUDGE_CONFIG` | Explicit configuration-file path |
| `NUDGE_CACHE_DIR` | Metadata-cache directory; default is `.cache` in the build's source directory |
| `NUDGE_AI_TIMEOUT` | Request timeout in seconds; default 15 |
| `NUDGE_CODEX_TIMEOUT`, `NUDGE_CLAUDE_TIMEOUT`, `NUDGE_OLLAMA_TIMEOUT`, `NUDGE_LOCAL_TIMEOUT` | Provider-specific timeouts when `NUDGE_AI_TIMEOUT` is unset |

`--provider`, `--model`, and `--endpoint` override their respective settings for
one command. Request timeouts are configured through the environment. `--force-ai` forces eligible command selection through
the configured model for diagnostics; local-only mode takes precedence.
`--force-codex` remains a legacy Codex-specific diagnostic option.

## Codex

Install the Codex CLI and sign in using `codex login` with your subscription
account. Nudge checks `codex login status`, requires ChatGPT authentication,
rejects API authentication, and removes API-key overrides from the subprocess.
It uses an isolated, ephemeral selection request with tools disabled.

```bash
./target/release/nudge-rust config --provider codex --model gpt-6-luna
```

Nudge delegates authentication to the CLI. It does not copy tokens or add an API
billing path. Subscription usage limits and account-level extra-usage settings
remain controlled by the provider. A configured model must support the requested
structured response and be available to the account.

## Claude Code

Install Claude Code and sign in through `claude auth login`. Nudge checks
`claude auth status --json` for a `claude.ai` / `firstParty` login. API keys,
token overrides, and cloud-provider authentication are rejected.

```bash
./target/release/nudge-rust config --provider claude --model haiku
```

The request runs from a temporary directory with safe mode, user/project settings
excluded, hooks disabled, no built-in tools, no MCP servers or skills, and no
persisted conversation. `CLAUDE_CONFIG_DIR` is retained if explicitly configured;
other Claude/Anthropic environment overrides are stripped. Organization-managed
policy remains under the CLI's control.

The adapter was checked with Claude Code 2.1.316. Older versions may lack required
flags; Nudge does not retry with weaker isolation. CLI/model availability is
provider-controlled, so changing the model does not guarantee a usable selection.

## Local inference

Start a local server and install or load a model using its own tools. Nudge does
not download weights or install an inference runtime. Local HTTP requires `curl`.

```bash
./target/release/nudge-rust models --provider ollama
./target/release/nudge-rust config --provider ollama --model YOUR_INSTALLED_MODEL_ID

./target/release/nudge-rust models --provider local --endpoint http://127.0.0.1:1234/v1
./target/release/nudge-rust config --provider local --model YOUR_MODEL_ID --endpoint http://127.0.0.1:1234/v1
```

Ollama uses `/api/show`, `/api/chat`, and `/api/tags`. The `local` provider uses
OpenAI-compatible `/chat/completions` and `/models`, such as a configured LM Studio
or llama.cpp server. Both request a non-streaming, schema-constrained result.

Only HTTP loopback endpoints are accepted. Remote addresses, URL credentials,
query strings, proxies, redirects, and server HTTP authentication are unsupported.
Ollama model metadata is checked and known remote-backed entries are declined.
For an OpenAI-compatible server, the user must ensure it actually performs local
inference: a loopback address alone cannot establish where the server sends data.

The default timeout is 15 seconds. `NUDGE_AI_TIMEOUT` can be increased for slow
model loading. Ollama is asked to retain the model for five minutes. A `local-llm`
source label means model inference; `local` means deterministic matching.

Protocol behavior is tested against controlled HTTP servers. Compatibility and
accuracy have not been certified for every server version or model.

## Data sent and failure handling

No provider receives terminal scrollback, unrelated history, or command output.
The argument-aware adapters send command-syntax slots and eligible routes while
omitting paths, IDs, option values, and other preserved operands. The older
Herdr/Omarchy matcher accepts only literal command words and sends those words
with its shortlisted routes. Option corrections use local matching only.

A missing CLI/model, refused authentication, timeout, invalid response, or
out-of-range candidate produces no correction. Providers are not automatically
switched. Ctrl+C cancels the local request and terminates CLI subprocess groups;
a local HTTP server may continue inference until it notices disconnection.
