# CLI support and launch checklist

**Platform boundary: Linux and Bash only.** No Windows, PowerShell, or macOS
support is planned. Cross-platform executables are tested only on Linux.
Windows package managers (`winget`, `scoop`, `choco`) and Homebrew are excluded
from this inventory.

The launch requirement is coverage of mainstream Linux command-line workflows
and popular developer tools. This inventory makes that requirement reviewable;
it is not an exhaustive popularity ranking or a statement of implemented support.
Add missing mainstream tools to this checklist during development. Requests for
niche tools use the [request template](CLI_REQUEST_TEMPLATE.md).

The [additional Linux CLI roadmap](CLI_ADDITIONS.md) records the full requested
expansion, including the top-priority additions and desktop/Wayland tools.

The [first implemented CLI batch](FIRST_CLI_BATCH.md) documents the initial
Git, Docker/Compose, systemctl, and journalctl adapters and their test results.
The [Linux profile batch](LINUX_PROFILES.md) adds 110 individually listed,
tested, scoped adapters. The inventory below identifies registered tools; detailed
per-command matrices define the actual supported forms and exclusions.
The [nested CLI batch](NESTED_CLI_BATCH.md) adds Nix, iwctl, Zellij, and strace,
bringing the registry at that point to 120 executable names.
All tools absent from these implementation reports remain planned.

Current registry: **267 executable names**. See the [latest expansion](CLI_EXPANSION.md)
and [complete requested-status ledger](CLI_STATUS.md) before assuming a listed
tool or nested command is supported.

## Coverage inventory

Every executable needs an individual implementation and validation entry before
it is listed as a scoped adapter. A tool with only a few supported command forms
must list those forms and its exclusions explicitly.
Help output alone does not establish support, and compatibility with one version
does not establish compatibility with every version or implementation.

| Area | Launch inventory | Current status |
|---|---|---|
| Existing integrations | `omarchy`, `herdr` | Scoped adapters: `omarchy`, `herdr`. See batch reports for exact forms. |
| Files and directories | `ls`, `cp`, `mv`, `rm`, `mkdir`, `rmdir`, `touch`, `ln`, `stat`, `file`, `readlink`, `realpath`, `basename`, `dirname`, `du`, `df`, `install`, `mktemp` | Scoped adapters: `ls`, `cp`, `mv`, `mkdir`, `rmdir`, `touch`, `ln`, `stat`, `file`, `readlink`, `realpath`, `basename`, `dirname`, `du`, `df`, `mktemp`. Remaining names planned. |
| Text and search | `cat`, `head`, `tail`, `less`, `more`, `grep`, `rg`, `find`, `fd`, `locate`, `sed`, `awk`, `sort`, `uniq`, `cut`, `paste`, `tr`, `wc`, `tee`, `xargs`, `diff`, `patch`, `strings` | Scoped adapters: `cat`, `head`, `tail`, `less`, `more`, `grep`, `rg`, `fd`, `locate`, `sed`, `awk`, `sort`, `uniq`, `cut`, `paste`, `tr`, `wc`, `tee`, `diff`, `patch`, `strings`. Remaining names planned. |
| Archives and checksums | `tar`, `gzip`, `gunzip`, `bzip2`, `bunzip2`, `xz`, `unxz`, `zip`, `unzip`, `7z`, `sha256sum`, `sha512sum`, `md5sum` | Scoped adapters: `tar`, `gzip`, `gunzip`, `bzip2`, `bunzip2`, `xz`, `unxz`, `sha256sum`, `sha512sum`, `md5sum`. Remaining names planned. |
| Processes and jobs | `ps`, `pgrep`, `pkill`, `kill`, `killall`, `top`, `htop`, `btop`, `nice`, `renice`, `nohup`, `timeout`, `watch`, `time` | Scoped adapters: `ps`, `pgrep`, `top`, `htop`, `btop`, `nice`, `timeout`, `watch`. Remaining names planned. |
| Services and system information | `systemctl`, `journalctl`, `loginctl`, `hostnamectl`, `timedatectl`, `localectl`, `dmesg`, `uname`, `hostname`, `uptime`, `date`, `free`, `lscpu`, `lspci`, `lsusb`, `env`, `printenv`, `which`, `whereis` | Scoped adapters: `systemctl`, `journalctl`, `loginctl`, `hostnamectl`, `timedatectl`, `localectl`, `dmesg`, `uname`, `hostname`, `uptime`, `date`, `free`, `lscpu`, `lsusb`, `env`, `printenv`, `which`. Remaining names planned. |
| Networking and transfers | `ip`, `ss`, `ping`, `traceroute`, `tracepath`, `dig`, `host`, `nslookup`, `resolvectl`, `nmcli`, `curl`, `wget`, `ssh`, `scp`, `sftp`, `rsync`, `nc`, `nmap`, `tcpdump`, `ufw`, `firewall-cmd` | Scoped adapters: `ss`, `resolvectl`, `curl`, `wget`, `rsync`, `nmap`, `tcpdump`, `ufw`. Remaining names planned. |
| Ownership, users, and storage | `chmod`, `chown`, `chgrp`, `id`, `whoami`, `who`, `groups`, `getent`, `passwd`, `useradd`, `usermod`, `userdel`, `groupadd`, `groupdel`, `lsblk`, `blkid`, `findmnt`, `mount`, `umount` | Scoped adapters: `id`, `who`, `getent`, `lsblk`, `blkid`, `findmnt`, `mount`. Remaining names planned. |
| Package management | `pacman`, `yay`, `paru`, `flatpak`, `apt`, `apt-get`, `apt-cache`, `dpkg`, `dnf`, `rpm`, `zypper`, `apk`, `snap` | Scoped adapters: `pacman`, `yay`. Remaining names planned. |
| Version control and hosting | `git`, `gh`, `glab` | Scoped adapters: `git`, `gh`. Remaining names planned. |
| Containers and orchestration | `docker`, `docker compose`, `docker-compose`, `podman`, `podman compose`, `nerdctl`, `ctr`, `kubectl`, `helm`, `minikube`, `kind` | Scoped adapters: `docker`, `docker compose`, `docker-compose`, `podman`, `nerdctl`, `ctr`, `kubectl`, `helm`. Remaining names planned. |
| Languages, builds, and environments | `cargo`, `rustup`, `rustc`, `python`, `python3`, `pip`, `pip3`, `uv`, `poetry`, `pipx`, `node`, `npm`, `npx`, `pnpm`, `yarn`, `bun`, `deno`, `go`, `make`, `cmake`, `ninja`, `gcc`, `g++`, `clang`, `java`, `javac`, `mvn`, `gradle`, `dotnet`, `gem`, `bundle`, `composer`, `mise` | Scoped adapters: `cargo`, `rustup`, `rustc`, `python`, `python3`, `pip`, `pip3`, `uv`, `node`, `npm`, `deno`, `make`, `cmake`, `ninja`. Remaining names planned. |
| Data and databases | `jq`, `yq`, `sqlite3`, `psql`, `mysql`, `mariadb`, `redis-cli` | Scoped adapters: `jq`, `sqlite3`, `psql`. Remaining names planned. |
| Cloud and infrastructure | `aws`, `gcloud`, `az`, `terraform`, `tofu`, `ansible`, `ansible-playbook` | Remaining names planned. |
| Interactive tools and editors | `tmux`, `screen`, `fzf`, `zoxide`, `bat`, `eza`, `vim`, `nvim`, `nano`, `code` | Scoped adapters: `screen`, `fzf`, `zoxide`, `bat`, `eza`, `vim`, `nvim`, `nano`. Remaining names planned. |
| AI command-line tools | `codex`, `claude`, `ollama` | Remaining names planned. |
| Shell builtins and wrappers | `cd`, `pwd`, `export`, `unset`, `source`, `type`, `command`, `history`, `jobs`, `fg`, `bg`, `alias`, `unalias`, `sudo`, `doas` | Remaining names planned. |

`ctr` and `nerdctl` are the containerd client targets. Treating the containerd
daemon as an interchangeable client would be incorrect. Nested CLIs such as
`docker compose` need their own metadata/version checks.

GNU, BusyBox, and Linux distribution-specific variants must be identified
and tested separately where their syntax differs. For example, two programs
named `yq` need not share a command grammar. Tools such as `kill`, `pwd`, and
`time` can also resolve to a shell builtin or keyword rather than a file.

## Definition of supported

For each executable, record:

1. **Discovery:** how its installed version and command/flag definitions are
   identified using read-only metadata or reviewed, versioned adapter data.
   Discovery must not execute user workloads just to learn command syntax.
2. **Coverage:** exact supported subcommands, flags, argument positions, aliases,
   and version ranges. Do not guess a grammar solely from a model response.
3. **Argument handling:** preserve paths, resource identifiers, quoted values,
   option values, positional arguments, and `--` boundaries. Unknown or ambiguous
   forms must be declined. Correcting syntax must not rename the user's target.
4. **Failure handling:** distinguish a likely syntax error from a valid command
   that failed because of permissions, connectivity, authentication, missing
   resources, or application state. Do not suggest a speculative retry for those
   runtime failures.
5. **Effects:** identify commands that mutate data or services and specify which
   corrections are eligible. Never add privileges, broaden a target, or introduce
   destructive/force flags as a guessed correction. Risky forms can be excluded
   explicitly even when other commands from the tool are supported.
6. **Verification:** positive examples, ambiguous/negative examples, version
   fixtures, argument preservation, Enter/cancel behavior, interruption, and
   representative timing. Use fixtures or disposable resources for mutating
   commands. Report real-runtime checks separately from simulated tests.

The main executable must still be typed correctly. Unrecognized executables,
unsupported syntax, pipelines, expansions, and compound commands remain outside
scope until their handling is explicitly implemented and verified. Interactive
application commands and REPL input are not Bash command corrections.

## Release gates

- [x] Implement initial argument-aware parsing and scoped Git/Docker/systemd
  adapters beyond the catalog-based subcommand matchers.
- [ ] Expand argument/grammar coverage and validate additional tool versions.
- [ ] Track each inventory executable with tested forms, versions, exclusions,
  and implementation status; complete mainstream coverage before public launch.
- [ ] Verify on clean Linux installations from multiple distribution families with
  representative installed tools.
- [x] Document scoped command coverage and measured local latency.
- [ ] Publish release artifacts and verify their documented coverage.
- [ ] Confirm Linux CI passes on the hosted runner and enable private vulnerability
  reporting in repository settings before announcing a release.
- [x] Implement per-user install/uninstall, updates, rollback, and static x86_64
  packaging; validate lifecycle behavior in four isolated distribution userspaces.
  See [the distribution report](DISTRIBUTION_TESTS.md).
- [ ] Verify the final published downloads; local package tests alone do not
  establish release readiness.
- [x] Create the public Nudge issue tracker, link it from the README, and expose
  the niche-tool request template in its new-issue flow.

## Adding a requested tool

Confirm the executable and its implementation/version first, collect the example
corrections and refusal cases, then add a catalog/parser adapter and tests. Update
the support matrix and changelog with the actual supported forms. A request is
not a support claim: keep it marked planned until those checks pass.
