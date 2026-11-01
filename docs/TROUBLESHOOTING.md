# Troubleshooting

Nudge supports Linux and interactive Bash 5+. Start with a fresh shell after
installing, updating, or rolling back: `exec bash`.

## No suggestion appears

Check `command -v nudge`, the managed setup block in `~/.bashrc`, and whether
`NUDGE_ENABLED` is unset or `1`. For source-only development, use
`target/release/nudge-rust` instead of `nudge` below.

```bash
nudge supported
nudge suggest --local-only --command 'git statsu' --status 1
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
nudge config
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
NUDGE_CACHE_DIR="$nudge_test_cache" nudge suggest --local-only --command 'git statsu'
```

The default cache is `${XDG_CACHE_HOME:-$HOME/.cache}/nudge`; `NUDGE_CACHE_DIR`
overrides it. Installed copies do not depend on the source checkout.

## Installer refuses shell setup or an update

An earlier manual `nudge.bash` source block must be removed before automatic
setup. A symlinked startup file or a block edited after installation requires
manual setup with `--no-modify-shell`, or review of the existing block. Nudge
refuses to overwrite unrelated launchers and unowned installation directories.

A `.lock` file prevents overlapping installation operations. If an operation
was interrupted, confirm no installer is running before removing that file from
the installation directory. Do not remove a live installer's lock.

Use `nudge rollback` to restore the previous installed payload, then `exec bash`.
See [installation and update details](INSTALLATION.md) for custom prefixes,
backups, path restrictions, and interrupted-operation behavior.

## Disable or remove Nudge

Set `NUDGE_ENABLED=0` to disable the hook in the current shell. Run
`nudge uninstall` and start a fresh shell to remove a managed installation.
Settings, cache, startup-file backups, and unrelated shell content are retained.
For a manual source-only setup, remove its source block yourself. See
[removal instructions](INSTALLATION.md#uninstall).
