# Package-managed and manual staged installation

Nudge supports Linux and interactive Bash 5+. These installations expose the
command `nudge-bash` to avoid collisions with unrelated software named `nudge`.
Examples using `nudge` in provider documentation also apply to `nudge-bash`.

## Build from source

Build as your normal user with Rust 1.88+, Cargo, GNU Make, and Python 3 (notice
collection only):

```bash
make
sudo make install PREFIX=/usr
```

For a manual user-prefix installation, run `make install PREFIX="$HOME/.local"`
instead. The default prefix is `/usr/local`. This installation uses a fixed layout;
the separate `./install.sh` provides the existing per-user release/rollback layout.
Choose one installation method. No Makefile target edits shell startup files.

Packagers stage files with `make install DESTDIR="$pkgdir" PREFIX=/usr`.
Installation copies prepared artifacts and never invokes Cargo. `BINARY` and
`NOTICE_DIR` select prepared binary and notice paths. From an extracted release
bundle, use `BINARY=bin/nudge NOTICE_DIR=.`; no build toolchain is required.

## Enable in Bash

Remove any earlier Nudge activation line or managed setup block before switching
installation methods. Add this line to your own `~/.bashrc` for a `/usr` install:

```bash
[[ -r /usr/lib/nudge-bash/nudge.bash ]] && source /usr/lib/nudge-bash/nudge.bash
```

For a different prefix, change that path, for example
`$HOME/.local/lib/nudge-bash/nudge.bash`. Start a fresh Bash shell. The readability
guard keeps startup quiet after removal. Optional Bash management-command
completion is installed for `bash-completion`; it does not enable the hook.

## Update and remove

For an AUR package, update with your usual package manager and remove with
`sudo pacman -R nudge-bash` or `sudo pacman -R nudge-bash-bin`, as appropriate.
For a manual Makefile installation, rebuild and reinstall to update, or use
`sudo make uninstall PREFIX=/usr` with the same prefix to remove it. Omit sudo
for a user-owned prefix. Never use `make uninstall` for pacman-owned files.

The package marker prevents Nudge's per-user `install`, `uninstall`, and
`rollback` actions from operating from this installation. Use the external
installation method instead. Settings and caches remain in the user's XDG
directories; package installation/removal does not read, alter, or delete them.

## Providers

Local corrections work without a provider. Codex, Claude Code, and local LLMs
are optional; local HTTP backends also need `curl` and a running model server.
Run `nudge-bash config` to inspect settings. No package script authenticates a
provider or requests a model response. See [provider setup](PROVIDERS.md).
