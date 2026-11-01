# Nudge

Fast, local-first command correction for Bash on Linux. Nudge checks a failed
command, offers a correction, and waits for **Enter** before running it. Press any
other key to cancel.

```text
$ git statsu
…unknown subcommand…

git status
[Enter to run · any other key to cancel]
```

Nudge is written in Rust for **Linux and Bash 5+**. It does not require a specific
Linux distribution or desktop environment. It is under active development;
command coverage and a standalone installer are not yet complete.

## How it works

- A Bash prompt hook checks failed commands without replacing the shell.
- Local rules correct unambiguous syntax errors using reviewed adapters and
  installed command metadata.
- Optional model selection supports **Codex**, **Claude Code**, and **local LLMs**
  through Ollama or a local server implementing the OpenAI-compatible API.
- The proposed command is displayed before execution. Arguments are passed
  literally; model output is never evaluated as shell code.

The executable name must be correct: `git statsu` can become `git status`, but
`gti status` is ignored. Valid commands that fail because of permissions,
connectivity, or missing resources are not automatically retried.

## Build and enable

Requirements: Linux, Bash 5+, and Rust 1.88 or newer to build. Running Nudge
requires the compiled binary and Bash hook. Local LLM support also requires
`curl` and a separately running inference server.

```bash
git clone https://github.com/gammamike/nudge.git
cd nudge
cargo build --locked --release
```

The executable is currently named `target/release/nudge-rust`.

To try it in a separate shell:

```bash
./try-bash
```

To enable it in normal interactive shells, add a guarded source block to
`~/.bashrc`, replacing `/absolute/path/to/nudge` with this checkout's location:

```bash
if [[ -r /absolute/path/to/nudge/nudge.bash &&
      -x /absolute/path/to/nudge/target/release/nudge-rust ]]; then
    source /absolute/path/to/nudge/nudge.bash
fi
```

Run `exec bash` or open a new terminal. Keep the checkout in place: the hook uses
its release executable. Rebuild after updating the source, then start a new shell
to load any newly registered executables.

To disable Nudge for the current shell:

```bash
export NUDGE_ENABLED=0
```

To remove Nudge, delete its source block from `~/.bashrc` and start a new shell,
then remove the checkout if you no longer need it. Configuration is kept in
`~/.config/nudge/config.json` by default, or the configured XDG/override path.
Remove that file separately if you want to discard saved settings.

To update an existing checkout:

```bash
git pull --ff-only
cargo build --locked --release
exec bash
```

## Local corrections and model providers

To use deterministic local corrections without any model calls:

```bash
export NUDGE_LOCAL_ONLY=1
```

Unset that variable, or set it to `0`, to allow the selected provider. Models are
optional; missing authentication or an unavailable provider produces no model
suggestion. Nudge does not switch providers automatically.

Choose one provider; the following are alternatives, not a setup sequence:

| Provider | Saved configuration example |
|---|---|
| Codex subscription CLI | `./target/release/nudge-rust config --provider codex --model YOUR_MODEL_ID` |
| Claude Code subscription CLI | `./target/release/nudge-rust config --provider claude --model YOUR_MODEL_ID` |
| Local LLM with Ollama | `./target/release/nudge-rust config --provider ollama --model YOUR_INSTALLED_MODEL_ID` |
| Local LLM with a compatible HTTP server | `./target/release/nudge-rust config --provider local --model YOUR_MODEL_ID --endpoint http://127.0.0.1:1234/v1` |

Replace model placeholders with an available model ID or supported alias. Run
`./target/release/nudge-rust config` to inspect effective settings. Local models
can be listed with `models --provider ollama` or `models --provider local`.

Codex is the default provider; Claude Code and local LLMs are selectable
alternatives. Codex and Claude Code use their CLI's existing subscription login
and reject API-key authentication. Provider limits and account-level billing
settings still apply. Local inference requires a model loaded on your server.

See [provider configuration](docs/PROVIDERS.md) for authentication, local server
endpoints, model overrides, privacy boundaries, and environment settings.

## Command coverage

The registry currently contains **120 executable adapters**, with deliberately
scoped support. It includes Git, Docker/Compose, systemd, common file/text tools,
desktop utilities, Cargo, Pacman/Yay query operations, Nix, iwctl, Zellij, and strace.
A listed executable does not imply support for every option or subcommand.

- [Git, Docker/Compose, and systemd support](docs/FIRST_CLI_BATCH.md)
- [Additional Linux profiles, exact scopes, and timings](docs/LINUX_PROFILES.md)
- [Nix, iwctl, Zellij, and strace scopes and tests](docs/NESTED_CLI_BATCH.md)
- [Launch coverage checklist](docs/CLI_SUPPORT.md)
- [Additional requested tools](docs/CLI_ADDITIONS.md)

List registered executable names:

```bash
./target/release/nudge-rust supported
```

Inspect a suggestion without executing it:

```bash
./target/release/nudge-rust suggest --local-only --command 'git statsu'
```

Pipelines, shell expansions, compound commands, executable-name typos, and Bash
aliases/functions are outside the current scope. Commands omitted from shell
history are skipped. Destructive and privilege-changing forms are excluded or
restricted by the individual adapter.

## Request another tool

[Open a CLI support request](https://github.com/gammamike/nudge/issues/new?template=cli-support.yml)
with the executable, Linux distribution, version, and examples of expected
corrections. Include cases that should be left alone. Replace private paths,
credentials, hostnames, and resource identifiers with placeholders.

Check [existing requests](https://github.com/gammamike/nudge/issues) first. The
[request guide](docs/CLI_REQUEST_TEMPLATE.md) explains the information needed to
review a new adapter.

## Development

```bash
cargo build --locked --release
cargo fmt --check
cargo clippy --locked --all-targets -- -D warnings
cargo test --locked
python3 -m unittest discover -s tests -v
bash -n nudge.bash interactive.bash try-bash
```

Integration tests require Python 3 and `curl`. They exercise the Rust binary
using captured metadata, mock executables, and loopback servers. No model login
or live model requests are needed.

See [contribution guidelines](CONTRIBUTING.md), [development notes](docs/DEVELOPMENT.md),
and the [changelog](CHANGELOG.md). For setup problems, see
[troubleshooting](docs/TROUBLESHOOTING.md).

## License

[GNU General Public License v3.0 only](LICENSE) (`GPL-3.0-only`).
