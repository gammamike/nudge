# Additional Linux CLI roadmap

The [AI CLI batch](AI_CLI_BATCH.md) adds four scoped adapters, bringing the
current registry to **271 executable names**.

Entries here are a roadmap, not support claims merely because they are listed.
The first implemented batch is Git, Docker/Compose, systemctl, and journalctl;
its scoped support and completed tests are recorded in [the batch report](FIRST_CLI_BATCH.md).
The [latest expansion](CLI_EXPANSION.md) adds another 147 executable adapters
and Docker Buildx inspection, for **267 executable names**. The
[status ledger](CLI_STATUS.md) identifies the remaining requested tools.

The [Linux profile batch](LINUX_PROFILES.md) now records 110 implemented,
tested adapters. The [nested CLI batch](NESTED_CLI_BATCH.md) adds Nix, iwctl,
Zellij, and strace, bringing top-priority coverage to 18 of the 21 names below.
Coverage is deliberately scoped per tool; boot/key operations are mostly
inspection-only. Names absent from the implementation reports remain planned.

**Linux and Bash only.** No Windows, PowerShell, or macOS support. `winget`,
`scoop`, `choco`, and Homebrew are excluded. Cross-platform tools refer only to
their Linux builds. `zsh` and `fish` below are possible executable targets, not
additional shell integrations. Repeated names across categories are the same
backlog item; the priority list is an index, not additional implementations.

## Top priority additions

`nix`, `hyprctl`, `crontab`, `ssh-keygen`, `openssl`, `gpg`, `ffmpeg`, `lsof`,
`strace`, `wl-copy`, `wl-paste`, `xdg-open`, `wpctl`, `bluetoothctl`, `iwctl`,
`mkinitcpio`, `limine`, `zellij`, `lazygit`, `man`, `tldr`.

## Requested inventory

| Area | Planned Linux executable/command targets |
|---|---|
| Desktop / Wayland | `hyprctl`, `hyprpaper`, `hyprlock`, `hypridle`, `waybar`, `walker`, `mako`, `makoctl`, `notify-send`, `wl-copy`, `wl-paste`, `grim`, `slurp`, `xdg-open`, `xdg-mime`, `playerctl`, `brightnessctl`, `wpctl`, `pactl`, `pamixer`, `bluetoothctl`, `iwctl`, `swww`, `wlr-randr`, `gsettings`, `fc-list`, `fc-cache` |
| Boot, kernel, and low-level system | `mkinitcpio`, `dracut`, `limine`, `grub-mkconfig`, `bootctl`, `efibootmgr`, `modprobe`, `lsmod`, `rmmod`, `sysctl`, `udevadm`, `systemd-analyze`, `systemd-run`, `coredumpctl`, `networkctl`, `busctl`, `reflector`, `fwupdmgr` |
| Disks and filesystems | `fdisk`, `parted`, `gdisk`, `mkfs`, `fsck`, `dd`, `sync`, `cryptsetup`, `lvs`, `pvs`, `vgs`, `lvcreate`, `btrfs`, `snapper`, `zfs`, `zpool`, `mdadm`, `smartctl`, `swapon`, `swapoff` |
| Debugging and performance | `lsof`, `fuser`, `strace`, `ltrace`, `gdb`, `perf`, `valgrind`, `ldd`, `objdump`, `nm`, `iotop`, `vmstat`, `iostat`, `nethogs`, `iftop`, `hyperfine` |
| Hardware information | `sensors`, `nvidia-smi`, `nvtop`, `powertop`, `upower`, `cpupower`, `dmidecode`, `lshw`, `inxi`, `fastfetch` |
| Security and keys | `ssh-keygen`, `ssh-add`, `ssh-copy-id`, `ssh-agent`, `gpg`, `openssl`, `age`, `sops`, `pass`, `certbot`, `visudo`, `nft`, `iptables`, `fail2ban-client`, `getfacl`, `setfacl`, `chattr`, `lsattr` |
| Scheduling | `crontab`, `at`, systemd timers through `systemctl list-timers` |
| Text and files | `tree`, `column`, `tac`, `rev`, `nl`, `fold`, `fmt`, `join`, `comm`, `split`, `shuf`, `seq`, `base64`, `xxd`, `hexdump`, `od`, `iconv`, `envsubst`, `rename`, `shred`, `truncate`, `inotifywait`, `entr` |
| Networking | `iw`, `ethtool`, `mtr`, `netstat`, `arp`, `whois`, `wg`, `wg-quick`, `tailscale`, `openvpn`, `socat`, `http` (HTTPie), `aria2c`, `iperf3` |
| Containers | `docker buildx`, `buildah`, `skopeo`, `k9s`, `kubectx`, `kubens`, `kustomize`, `k3s`, `distrobox`, `toolbox`, `lazydocker` |
| Version control | `lazygit`, `tig`, `git-lfs`, `pre-commit`, `jj` |
| Languages and tooling | `pyenv`, `conda`, `mamba`, `virtualenv`, `pytest`, `ruff`, `black`, `mypy`, `nvm`, `fnm`, `asdf`, `tsc`, `eslint`, `prettier`, `vite`, `vitest`, `jest`, `rustfmt`, `gofmt`, `golangci-lint`, `zig`, `ruby`, `rails`, `php`, `artisan`, `lua`, `luarocks`, `perl`, `mix`, `ghc`, `cabal`, `stack`, `kotlin`, `swift`, `meson`, `bazel`, `just`, `task`, `pkg-config`, `makepkg` |
| Package management | `nix`, `nix-shell`, `nix-env`, `nixos-rebuild`, `home-manager`, `emerge`, `xbps-install`, `pkg`, `paccache`, `pamac`, `topgrade` |
| Data and databases | `pg_dump`, `pg_restore`, `mysqldump`, `mongosh`, `duckdb`, `sqlcmd`, `clickhouse-client`, `csvkit`, `qsv` |
| Cloud and deployment | `doctl`, `flyctl`, `vercel`, `netlify`, `wrangler`, `heroku`, `railway`, `firebase`, `supabase`, `pulumi`, `packer`, `vagrant`, `eksctl`, `hcloud`, `vault`, `gsutil`, `bq`, `cdk`, `sam` |
| Media and documents | `ffmpeg`, `ffprobe`, `magick`, `yt-dlp`, `mpv`, `pandoc`, `exiftool`, `qpdf`, `pdftk`, `gs`, `sox` |
| Shell, dotfiles, and help | `man`, `tldr`, `info`, `apropos`, `zsh`, `fish`, `chsh`, `direnv`, `stow`, `chezmoi`, `starship`, `atuin`, `echo`, `printf`, `read`, `test`, `eval`, `exec`, `trap`, `set`, `ulimit`, `umask`, `wait`, `disown` |
| Interactive tools and editors | `zellij`, `byobu`, `hx` (Helix), `emacs`, `micro`, `yazi`, `ranger`, `nnn`, `lf`, `broot`, `glow` |
| Modern replacements | `dust`, `duf`, `procs`, `sd`, `delta`, `lsd`, `btm`, `tokei` |
| AI command-line tools | `gemini`, `aider`, `opencode`, `llm`, `gh copilot`, `goose`, `crush`, `amp`, `cursor-agent` |

## Implementation notes

- Verify executable identity and Linux availability before building an adapter.
  `pkg` is ambiguous and needs an identified Linux implementation; this entry
  does not add FreeBSD support. `csvkit` names a suite, so track its concrete
  executables individually. Aliases/functions such as some `nvm` installations
  need explicit shell handling.
- Nested targets such as `docker buildx`, `gh copilot`, and `systemctl list-timers`
  belong to their parent executable adapter but need their own command grammar.
- Disk formatting, encryption, boot changes, key operations, deletion, shell
  evaluation, and similar operations require narrow reviewed eligibility rules.
  Listing a tool is not authorization to guess destructive flags or targets.
- Follow the [support definition and release gates](CLI_SUPPORT.md#definition-of-supported).
  Record supported forms, negative cases, installed versions, and test results
  before changing any entry from planned to implemented.
