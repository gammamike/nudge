# Troubleshooting

Nudge supports Linux and interactive Bash 5+. Start with a fresh shell after
changing the source block or rebuilding: `exec bash`.

## No suggestion appears

Check that the release binary exists, the source block in `~/.bashrc` points to
the current checkout, and `NUDGE_ENABLED` is unset or `1`.

```bash
./target/release/nudge-rust supported
./target/release/nudge-rust suggest --local-only --command 'git statsu' --status 1
```

The second command prints a result without executing a correction. The executable
must be installed and spelled correctly. Its adapter must support the command
form, and its installed metadata must advertise the eligible syntax.

Success, interruption, valid syntax that failed at runtime, and commands omitted
from Bash history do not prompt. Aliases, functions, `sudo` wrappers, pipelines,
expansions, and compound commands are outside the current scope. Ambiguous or
unsupported syntax can legitimately produce no suggestion.

## Local corrections work, but model selection does not

```bash
./target/release/nudge-rust config
```

Check the selected provider and model, and whether `NUDGE_LOCAL_ONLY=1` disables
model calls. Environment variables override saved configuration. Providers do
not automatically fall back to one another.

- **Codex:** check the CLI's subscription login and model availability.
- **Claude Code:** check the CLI's subscription login, model availability, and
  support for the required isolation flags.
- **Local LLMs:** check that Ollama or the compatible local server is running,
  the model is installed or loaded, and `curl` is available. Confirm the loopback
  endpoint and list models with `models --provider ollama` or `models --provider local`.

See [provider configuration](PROVIDERS.md) for exact settings and authentication
requirements. Do not paste provider configuration or tokens into bug reports.

## Suggestions are slow or metadata seems stale

The first lookup may run metadata queries. Cached lookups are normally faster;
model requests add separate latency. Ctrl+C cancels the current request.

Help caching normally expires after one hour and also tracks executable metadata.
Wrappers, plugins, or toolchain changes can require a fresh cache. To diagnose
without deleting existing state, run a suggestion with an empty temporary cache:

```bash
nudge_test_cache=$(mktemp -d)
NUDGE_CACHE_DIR="$nudge_test_cache" ./target/release/nudge-rust suggest --local-only --command 'git statsu'
```

The default cache is `.cache` in the build's source directory; `NUDGE_CACHE_DIR`
overrides it. Keep the source checkout in place when using the current setup.

## Disable or remove Nudge

Set `NUDGE_ENABLED=0` to disable the hook in the current shell. Remove its source
block from `~/.bashrc` and start a new shell to disable it permanently. See
[setup and removal](../README.md#build-and-enable) for files to remove.
