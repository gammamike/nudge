# Installation, updates, and removal

Nudge runs on Linux in interactive Bash 5+. Installation is per-user and does
not require sudo, a system service, or a particular distribution. The engine and
installer are Rust; Bash supplies the shell integration. Codex, Claude Code, and
local LLMs are supported providers. **Codex cloud fallback is enabled by default**:
when local matching cannot choose an eligible correction, Nudge automatically
uses your existing Codex CLI login to request a selection from OpenAI. Selecting
Claude Code uses Anthropic; local LLM providers use a loopback server.

For deterministic local corrections only, add `export NUDGE_LOCAL_ONLY=1` to
`~/.bashrc` before starting a new shell, and run the same export in the current
shell. This disables every model request, including local LLMs. Enter confirms
command execution after a suggestion is available; it does not gate the preceding
model request. See [provider configuration](PROVIDERS.md) and
[what leaves your machine](../README.md#what-leaves-your-machine).

## Install from source

Install Rust 1.88+ and Cargo using your preferred Linux toolchain setup, then:

```bash
git clone https://github.com/gammamike/nudge.git
cd nudge
./install.sh
exec bash
```

`install.sh` builds the release executable and runs its `install` command.
A successful install copies the executable and embedded hook into a per-user
installation. The checkout can then be moved or removed. Keep a checkout if you
want to update from source.

Use `./install.sh --no-modify-shell` if you want to inspect the installation and
manage shell setup yourself; then source the hook path printed by the installer.
Installation makes no model requests. Its fallback notice reflects the current
environment and saved settings; exports loaded by a new Bash shell can change
the effective mode. The notice does not test authentication or server availability.

If you previously added a manual `nudge.bash` source block to `~/.bashrc`, remove
that block before using automatic setup. The installer refuses duplicate or
ambiguous setup. It does not rewrite unrelated shell configuration.

## Install a binary bundle

The packaging workflow builds an **x86_64 Linux** archive with a statically
linked musl executable, matching source archive, checksums, and license notices.
Download all three from [GitHub Releases](https://github.com/gammamike/nudge/releases).

Obtain the bundle, source archive, and `SHA256SUMS` from the same trusted release
location. In their download directory, verify and extract them. For example,
replace `0.1.2` below with the version you downloaded:

```bash
sha256sum -c SHA256SUMS
tar -xzf nudge-0.1.2-linux-x86_64.tar.gz
cd nudge-0.1.2-linux-x86_64
./install.sh
exec bash
```

Checksums detect changed files; they are not a signature or proof of who
published them. The bundle does not need Rust or Python at runtime. It requires
Bash 5+ and standard file utilities for the wrapper. The installed Rust CLI can
also install itself with `./bin/nudge install`. Alpine needs Bash installed;
its default `ash` shell is not a supported integration.

Only the x86_64 binary bundle is currently built and tested. Other Linux
architectures can be evaluated with source builds but are not release-verified.
No Windows, macOS, PowerShell, or additional shell integrations are provided.

## Paths and shell setup

| Item | Default location |
|---|---|
| CLI launcher | `~/.local/bin/nudge` |
| Installed releases and ownership record | `${XDG_DATA_HOME:-$HOME/.local/share}/nudge` |
| Active payload | `current` symlink within the installation directory |
| Previous payload | `previous` symlink within the installation directory |
| Bash startup file | `~/.bashrc` |
| Provider settings | `${XDG_CONFIG_HOME:-$HOME/.config}/nudge/config.json` |
| Metadata cache | `${XDG_CACHE_HOME:-$HOME/.cache}/nudge` |

Relative XDG directory values are ignored in favor of the home-directory
defaults. `NUDGE_CONFIG` and `NUDGE_CACHE_DIR` remain explicit overrides. Existing
checkout-local `.cache` directories are no longer used automatically.

The installer writes a marked block that adds the CLI directory to PATH once
and sources the installed hook. Existing prompt hooks are retained. It creates
a same-directory `BASHRC.nudge-backup-*` file before changing an existing startup
file and preserves that file's permissions. Repeating an identical installation
does not duplicate the block, move it, or create a new payload.

Custom locations are available:

```bash
./install.sh --prefix /absolute/path/to/prefix
./install.sh --bashrc /absolute/path/to/custom.bashrc
./install.sh --no-modify-shell
```

These examples are alternatives. `--prefix` selects `PREFIX/bin/nudge` and
`PREFIX/share/nudge`; settings and cache remain in their per-user XDG locations.
`--bashrc` selects a regular startup file. A symlinked startup file is preserved:
use `--no-modify-shell` and add the source line to your dotfile manager yourself.
The installer prints the installed hook path. Do not combine `--bashrc` with
`--no-modify-shell`.

Unrelated executables, unowned installation directories, edited/duplicate
managed blocks, and invalid installation links cause an error instead of being
overwritten. The installer accepts absolute UTF-8 paths without control
characters or `..` components; the binary directory cannot contain a colon.

## Update and rollback

From an existing source checkout:

```bash
git pull --ff-only
./install.sh
exec bash
```

For binary installations, verify and extract a new bundle, then run that bundle's
`./install.sh`. Reuse your `--prefix` when updating a custom installation from
an external bundle or checkout. Running an already-installed binary infers its
own installation directory.

A new payload is staged separately. The active `current` symlink is switched by
an atomic rename after the payload and shell setup are prepared. Interrupted or
failed operations can leave an inactive payload or stale lock; the current
payload is never overwritten in place. This is not a filesystem-wide transaction.
Older payload directories remain until uninstall; `previous` selects the most
recent rollback target.

```bash
nudge rollback
exec bash
```

Rollback swaps the current and previous payloads. It does not roll back provider
settings, caches, or unrelated shell changes. Restart Bash after updates and
rollback so its hook and supported-command registry match the active binary.
A `.lock` file prevents overlapping installer operations. Remove a stale lock
only after confirming that no installer is running.

## Uninstall

```bash
nudge uninstall
exec bash
```

Uninstall removes the owned launcher, installed payloads, and unchanged managed
Bash block. It preserves provider settings, metadata cache, startup-file backups,
and shell content outside the block. A launcher replaced with another program
is left alone. Unexpected top-level installation files or an edited managed
block require manual review before removal.

If the installed launcher is unavailable, use a trusted source/bundle binary
with `uninstall`, adding `--prefix` for a custom location. There is no automatic
purge option. Remove your saved settings and cache separately if desired.
