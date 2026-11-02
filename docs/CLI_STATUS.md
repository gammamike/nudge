# Requested command status

The registry contains **267 executable names**. This ledger preserves the
requested inventory and distinguishes scoped support from pending work.
The full requested inventory is **not yet complete**. See the
[expansion report](CLI_EXPANSION.md) and previous batch reports for exact scopes.
Nested commands are counted separately here only to show their status; they do
not add executable names to the registry.

| Area | Scoped support | Still pending |
|---|---|---|
| Existing integrations | `omarchy`, `herdr` | — |
| Files and directories | `ls`, `cp`, `mv`, `mkdir`, `rmdir`, `touch`, `ln`, `stat`, `file`, `readlink`, `realpath`, `basename`, `dirname`, `du`, `df`, `mktemp` | `rm`, `install` |
| Text and search | `cat`, `head`, `tail`, `less`, `more`, `grep`, `rg`, `fd`, `locate`, `sed`, `awk`, `sort`, `uniq`, `cut`, `paste`, `tr`, `wc`, `tee`, `diff`, `patch`, `strings` | `find`, `xargs` |
| Archives and checksums | `tar`, `gzip`, `gunzip`, `bzip2`, `bunzip2`, `xz`, `unxz`, `sha256sum`, `sha512sum`, `md5sum` | `zip`, `unzip`, `7z` |
| Processes and jobs | `ps`, `pgrep`, `top`, `htop`, `btop`, `nice`, `timeout`, `watch` | `pkill`, `kill`, `killall`, `renice`, `nohup`, `time` |
| Services and system information | `systemctl`, `journalctl`, `loginctl`, `hostnamectl`, `timedatectl`, `localectl`, `dmesg`, `uname`, `hostname`, `uptime`, `date`, `free`, `lscpu`, `lsusb`, `env`, `printenv`, `which` | `lspci`, `whereis` |
| Networking and transfers | `ss`, `resolvectl`, `curl`, `wget`, `rsync`, `nmap`, `tcpdump`, `ufw` | `ip`, `ping`, `traceroute`, `tracepath`, `dig`, `host`, `nslookup`, `nmcli`, `ssh`, `scp`, `sftp`, `nc`, `firewall-cmd` |
| Ownership, users, and storage | `id`, `who`, `getent`, `lsblk`, `blkid`, `findmnt`, `mount` | `chmod`, `chown`, `chgrp`, `whoami`, `groups`, `passwd`, `useradd`, `usermod`, `userdel`, `groupadd`, `groupdel`, `umount` |
| Package management | `pacman`, `yay` | `paru`, `flatpak`, `apt`, `apt-get`, `apt-cache`, `dpkg`, `dnf`, `rpm`, `zypper`, `apk`, `snap` |
| Version control and hosting | `git`, `gh` | `glab` |
| Containers and orchestration | `docker`, `docker compose`, `docker-compose`, `podman`, `nerdctl`, `ctr`, `kubectl`, `helm` | `podman compose`, `minikube`, `kind` |
| Languages, builds, and environments | `cargo`, `rustup`, `rustc`, `python`, `python3`, `pip`, `pip3`, `uv`, `node`, `npm`, `deno`, `make`, `cmake`, `ninja` | `poetry`, `pipx`, `npx`, `pnpm`, `yarn`, `bun`, `go`, `gcc`, `g++`, `clang`, `java`, `javac`, `mvn`, `gradle`, `dotnet`, `gem`, `bundle`, `composer`, `mise` |
| Data and databases | `jq`, `sqlite3`, `psql` | `yq`, `mysql`, `mariadb`, `redis-cli` |
| Cloud and infrastructure | — | `aws`, `gcloud`, `az`, `terraform`, `tofu`, `ansible`, `ansible-playbook` |
| Interactive tools and editors | `screen`, `fzf`, `zoxide`, `bat`, `eza`, `vim`, `nvim`, `nano` | `tmux`, `code` |
| AI command-line tools | — | `codex`, `claude`, `ollama` |
| Shell builtins and wrappers | — | `cd`, `pwd`, `export`, `unset`, `source`, `type`, `command`, `history`, `jobs`, `fg`, `bg`, `alias`, `unalias`, `sudo`, `doas` |
| Desktop / Wayland | `hyprctl`, `hyprpaper`, `hyprlock`, `hypridle`, `waybar`, `walker`, `mako`, `makoctl`, `notify-send`, `wl-copy`, `wl-paste`, `xdg-open`, `playerctl`, `brightnessctl`, `wpctl`, `pamixer`, `bluetoothctl`, `iwctl`, `gsettings`, `fc-list`, `fc-cache` | `grim`, `slurp`, `xdg-mime`, `pactl`, `swww`, `wlr-randr` |
| Boot, kernel, and low-level system | `mkinitcpio`, `dracut`, `limine`, `bootctl`, `efibootmgr`, `modprobe`, `lsmod`, `sysctl`, `udevadm`, `systemd-analyze`, `coredumpctl`, `networkctl`, `busctl` | `grub-mkconfig`, `rmmod`, `systemd-run`, `reflector`, `fwupdmgr` |
| Disks and filesystems | `fdisk`, `parted`, `sync`, `cryptsetup`, `snapper`, `smartctl`, `swapon` | `gdisk`, `mkfs`, `fsck`, `dd`, `lvs`, `pvs`, `vgs`, `lvcreate`, `btrfs`, `zfs`, `zpool`, `mdadm`, `swapoff` |
| Debugging and performance | `fuser`, `strace`, `ltrace`, `gdb`, `ldd`, `objdump`, `nm`, `vmstat`, `iostat`, `hyperfine` | `lsof`, `perf`, `valgrind`, `iotop`, `nethogs`, `iftop` |
| Hardware information | `sensors`, `nvidia-smi`, `upower`, `dmidecode`, `lshw`, `fastfetch`, `cpupower` | `nvtop`, `powertop`, `inxi` |
| Security and keys | `gpg`, `openssl`, `age`, `sops`, `visudo`, `getfacl` | `ssh-keygen`, `ssh-add`, `ssh-copy-id`, `ssh-agent`, `pass`, `certbot`, `nft`, `iptables`, `fail2ban-client`, `setfacl`, `chattr`, `lsattr` |
| Scheduling | `systemctl list-timers` | `crontab`, `at` |
| Text and files | `tree`, `column`, `tac`, `rev`, `nl`, `fold`, `fmt`, `join`, `comm`, `split`, `shuf`, `seq`, `base64`, `hexdump`, `od`, `iconv`, `envsubst`, `rename`, `inotifywait` | `xxd`, `shred`, `truncate`, `entr` |
| Networking | `ethtool`, `mtr`, `whois`, `wg`, `tailscale`, `http`, `aria2c` | `iw`, `netstat`, `arp`, `wg-quick`, `openvpn`, `socat`, `iperf3` |
| Containers | `docker buildx`, `buildah`, `skopeo`, `kustomize`, `lazydocker` | `k9s`, `kubectx`, `kubens`, `k3s`, `distrobox`, `toolbox` |
| Version control | `lazygit`, `pre-commit`, `git-lfs` | `tig`, `jj` |
| Languages and tooling | `pytest`, `ruff`, `black`, `mypy`, `rustfmt`, `ruby`, `luarocks`, `meson`, `just`, `pkg-config`, `makepkg`, `virtualenv` | `pyenv`, `conda`, `mamba`, `nvm`, `fnm`, `asdf`, `tsc`, `eslint`, `prettier`, `vite`, `vitest`, `jest`, `gofmt`, `golangci-lint`, `zig`, `rails`, `php`, `artisan`, `lua`, `perl`, `mix`, `ghc`, `cabal`, `stack`, `kotlin`, `swift`, `bazel`, `task` |
| Package management | `nix`, `paccache` | `nix-shell`, `nix-env`, `nixos-rebuild`, `home-manager`, `emerge`, `xbps-install`, `pkg`, `pamac`, `topgrade` |
| Data and databases | `pg_dump`, `pg_restore` | `mysqldump`, `mongosh`, `duckdb`, `sqlcmd`, `clickhouse-client`, `csvkit`, `qsv` |
| Cloud and deployment | — | `doctl`, `flyctl`, `vercel`, `netlify`, `wrangler`, `heroku`, `railway`, `firebase`, `supabase`, `pulumi`, `packer`, `vagrant`, `eksctl`, `hcloud`, `vault`, `gsutil`, `bq`, `cdk`, `sam` |
| Media and documents | `ffmpeg`, `ffprobe`, `yt-dlp`, `mpv`, `pandoc`, `qpdf`, `magick`, `sox` | `exiftool`, `pdftk`, `gs` |
| Shell, dotfiles, and help | `man`, `tldr`, `info`, `apropos`, `stow`, `chezmoi`, `starship`, `atuin`, `direnv` | `zsh`, `fish`, `chsh`, `echo`, `printf`, `read`, `test`, `eval`, `exec`, `trap`, `set`, `ulimit`, `umask`, `wait`, `disown` |
| Interactive tools and editors | `zellij`, `micro`, `glow` | `byobu`, `hx`, `emacs`, `yazi`, `ranger`, `nnn`, `lf`, `broot` |
| Modern replacements | `dust`, `duf`, `procs`, `sd`, `delta`, `lsd`, `btm`, `tokei` | — |
| AI command-line tools | — | `gemini`, `aider`, `opencode`, `llm`, `gh copilot`, `goose`, `crush`, `amp`, `cursor-agent` |

## Work still required

- Short-option-only tools such as `crontab`, `ssh-keygen`, and `lsof` need a
  deliberate correction strategy. Guessing among one-letter options is not
  enabled merely to claim executable coverage.
- Destructive/storage, process termination, user administration, firewall
  mutation, and shell-evaluation commands need individually reviewed grammars.
- Bash builtins and functions require a separate integration path. The current
  executable-only hook deliberately skips them, including `nvm` functions.
- `pkg` needs an identified Linux implementation. `csvkit` is a suite and needs
  concrete executable names. No Windows or macOS packages are included.
- Legacy `swww` needs separate metadata. The tested current package exposes
  `awww`; it does not establish compatibility with the old executable.
- Further cloud/deployment, language, package-manager, and application adapters
  still need per-version help capture, argument grammar, exclusions, and positive
  and negative tests. A registered parent such as `gh` or `podman` does not imply
  support for `gh copilot` or `podman compose`.
- Some candidate packages did not produce usable help in this environment:
  display/TTY-dependent tools, relocated binaries requiring extra runtime setup,
  and wrappers requiring their toolchain configuration. These remain pending.

Use the [CLI request guide](CLI_REQUEST_TEMPLATE.md) for missing tools and forms.
