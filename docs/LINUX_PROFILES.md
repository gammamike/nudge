# Linux profile batch

Implemented and checked on a Linux development machine on 2026-11-01: **110 new executable
adapters**, bringing the registry at that point to **116 executable names**.
The subsequent [nested CLI batch](NESTED_CLI_BATCH.md) brings the total to **120**.
Docker Compose is a nested Docker adapter, not another executable in that count. Linux and Bash 5+
only; the binary rejects non-Linux builds and the hook skips non-Linux shells.

This is scoped syntax correction, not complete CLI emulation. The remaining
[launch inventory](CLI_SUPPORT.md) and [additional roadmap](CLI_ADDITIONS.md) are
still open. The coverage batch did not publish a release or install extra CLI packages.

## Behavior and boundaries

- Each profile defines literal read-only help queries, eligible commands/options,
  and option arities in [the registry](../data/linux-profiles.json). A trailing `=`
  in a flag declaration means a required value; `?` means optional. These suffixes
  describe the grammar, not characters inserted into a user's command.
- Candidates must also appear in installed help. Advertised but unreviewed
  options/commands, and typos that could mean an excluded form, are declined.
  Unique one-edit corrections are local. Multiple errors and ambiguous local
  matches are declined; selected command slots may use the configured AI fallback.
- Paths, patterns, clipboard text, IDs, URLs, and option values are preserved as
  literal arguments. `--` ends option scanning. No executable-name correction,
  shell expansions, pipelines, aliases/functions, or commands inside interactive
  applications. A Bash alias such as `ls` will therefore bypass the executable
  adapter; this batch does not change the user's aliases.
- Command profiles correct the root subcommand and reviewed flags. They do not
  infer arbitrary nested grammars or validate every semantic constraint imposed
  by a tool. Flat profiles correct reviewed options, not positional words.
  Some profiles stop at the first operand to keep application payloads opaque.
- The model sees only an eligible command-syntax slot and candidate routes.
  Preserved arguments/values are excluded. Option typos do not call AI.
  Valid recognized syntax that failed at runtime is left alone.
- Suggestions always require Enter. The backend emits an absolute executable and
  NUL-delimited arguments; Bash does not evaluate generated shell text. Executable
  paths retain symlink basenames so rustup/multicall tools keep their behavior.
- Help is cached for one hour, keyed by executable path, target file metadata,
  literal help query, and accepted help exit statuses. This is not a guarantee
  against every wrapper/toolchain change inside that hour. Cargo aliases and PATH
  extensions are queried afresh in the current directory, including revalidation.
- The same embedded registry supplies `nudge-rust supported` and the Bash startup
  allowlist. After enabling the source block in `~/.bashrc`, new normal Bash shells
  load it; use `exec bash` to refresh an existing terminal.

## Important scopes

| Tool/family | Included | Deliberate limits |
|---|---|---|
| GNU/file/text tools | Reviewed long options and literal argument preservation | No rm/dd/shred adapter; force/delete flags excluded from this registry; some forms with target-directory or legacy syntax are conservatively declined |
| hyprctl | Inspection commands and reload; JSON/instance options | No dispatch, eval, batch, plugin, kill, output or keyword correction |
| wpctl | status/list/inspect, volume, mute, default, profile and route commands | IDs and volume values remain literal; unknown per-command flags declined |
| bluetoothctl | list/devices/show/info, scan, connect/disconnect, pair/trust and power | No remove/unpair or interactive submenu correction |
| wl-copy / wl-paste | Reviewed clipboard options | Copy text opaque after first operand; paste watch/command execution excluded |
| mkinitcpio | List hooks, hook help, autodetected modules, help/version | No image generation, presets, removal or boot changes |
| limine / bootctl | Version/help/status/list/installation inspection | No boot installation, enrollment or removal |
| gpg | List/check keys and signatures, fingerprints, verification | No generation, import/export, encryption/decryption, deletion or passphrase changes |
| openssl | version/list/ciphers, digests, verify, x509 inspection | Reviewed per-command single-dash options; no key generation or output-writing flags |
| ffmpeg / ffprobe | Reviewed single-dash long options; basic conversion and media inspection | No guessed overwrite `-y`; stream-specific colon options and unreviewed codec/filter options declined |
| Cargo | add/build/check/test/bench/doc/fetch/update/metadata/tree/search/info | Per-command installed help; aliases/extensions protected; no clean/install/publish; unreviewed toolchain/global flags declined |
| Pacman / Yay | Explicit `-Q` / `--query` workflows, including info/search/list/owns/check | No sync/install/remove/upgrade correction; combined operation forms such as `-Qi` are conservatively declined during correction |
| Remaining interactive/desktop tools | Reviewed options when launched from Bash | No keystrokes, REPL commands, or application configuration edits |

## Validation and speed

- Seven Rust unit tests; 51 integration tests, including a positive and
  valid-failure subcase for **every one of the 110 new profiles**; 1,823 unchanged
  catalog regression cases. Formatting, Clippy with warnings denied, and Bash
  syntax checks passed.
- All 110 positive cases also ran against **real installed metadata**, followed by
  25 warm-cache measurements per tool. Tests never executed their proposed file,
  package, desktop, media, or system operations. Enter/accept tests used mock
  executables; four new terminal cases cover cp, hyprctl, wpctl, and ffprobe.
- A fresh normal Bash session loaded one Nudge hook, all 116 names, and retained
  the existing mise/zoxide prompt hooks. Codex, Claude Code, and local LLM regression
  tests used mocks; this batch made no live model requests.
- Timing below includes launching Nudge and producing a local suggestion. It
  excludes the original command's runtime, Bash prompt rendering, user response,
  and AI latency. These are local development measurements, not a cross-machine
  performance guarantee. The median of per-tool warm medians was **1.405 ms**;
  the range was **1.273–17.238 ms**. Cargo pays for fresh alias discovery.

| Tool | Empty cache, one sample (ms) | Warm median (ms) | Warm p95 (ms) |
|---|---:|---:|---:|
| `ls` | 3.872 | 1.685 | 1.840 |
| `cp` | 4.149 | 1.665 | 1.845 |
| `hyprctl` | 5.576 | 1.374 | 1.760 |
| `wpctl` | 5.408 | 1.332 | 1.473 |
| `ffmpeg` | 29.450 | 2.166 | 2.413 |
| `ffprobe` | 36.263 | 5.720 | 7.329 |
| `openssl` | 8.641 | 1.313 | 1.497 |
| `cargo` | 29.516 | 17.238 | 20.782 |
| `pacman` | 7.570 | 1.405 | 1.635 |
| `yay` | 20.480 | 1.634 | 1.907 |

[Raw timing results](../tests/fixtures/linux-profile-benchmark.json),
[captured help](../tests/fixtures/linux-profile-help.json),
[version provenance](../tests/fixtures/linux-profile-versions.json), and
[positive cases](../tests/fixtures/linux-profile-cases.json) are checked in with
this repository. Version provenance identifies the owning package, or the actual
rustup-managed executable version. Only those installed versions were checked;
other releases/implementations are not certified by these fixtures.

Reproduce the metadata-only benchmark from the repository root:

```bash
python3 tests/benchmark_profiles.py --samples 25 --output /tmp/nudge-profile-benchmark.json
```

## Per-executable matrix

Each row has an installed-help fixture and a passing correction test. `Options`
means only the explicit flags in that tool's registry entry, intersected with
installed help; it does not mean all options in its manual. `Commands` lists the
reviewed subcommands. All other forms remain outside that row's coverage.

| Executable | Tested package/tool version | Coverage | Example typo → correction |
|---|---|---|---|
| `apropos` | man-db 2.13.1-2 | Options | `apropos --exatc` → `apropos --exact` |
| `base64` | coreutils 9.12-2 | Options | `base64 --decoed` → `base64 --decode` |
| `basename` | coreutils 9.12-2 | Options | `basename --multipel 'private operand'` → `basename --multiple 'private operand'` |
| `bat` | bat 0.26.1-3 | Options | `bat --numbre` → `bat --number` |
| `bluetoothctl` | bluez-utils 5.87-2 | Commands: `list`, `devices`, `paired-devices`, `show`, `info`, `scan`, `connect`, `disconnect`, `pair`, `trust`, `power` | `bluetoothctl deviecs` → `bluetoothctl devices` |
| `bootctl` | systemd 262.1-1 | Commands: `status`, `is-installed`, `list` | `bootctl statsu` → `bootctl status` |
| `brightnessctl` | brightnessctl 0.5.1-3 | Options | `brightnessctl --lits` → `brightnessctl --list` |
| `btop` | btop 1.4.7-1 | Options | `btop --debgu` → `btop --debug` |
| `cargo` | cargo 1.99.1 (5f94df478 2026-08-27) | Commands: `build`, `check`, `test`, `bench`, `doc`, `fetch`, `update`, `metadata`, `tree`, `search`, `info`, `add` | `cargo buidl` → `cargo build` |
| `cat` | coreutils 9.12-2 | Options | `cat --numbre` → `cat --number` |
| `column` | util-linux 2.42.4-1 | Options | `column --tabel` → `column --table` |
| `comm` | coreutils 9.12-2 | Options | `comm --check-ordre 'private operand' 'private operand'` → `comm --check-order 'private operand' 'private operand'` |
| `coredumpctl` | systemd 262.1-1 | Commands: `list`, `info` | `coredumpctl lits` → `coredumpctl list` |
| `cp` | coreutils 9.12-2 | Options | `cp --verboes 'private operand' 'private operand'` → `cp --verbose 'private operand' 'private operand'` |
| `curl` | curl 8.23.0-1 | Options | `curl --verboes` → `curl --verbose` |
| `cut` | coreutils 9.12-2 | Options | `cut --bytse 'private value'` → `cut --bytes 'private value'` |
| `date` | coreutils 9.12-2 | Options | `date --daet 'private value'` → `date --date 'private value'` |
| `df` | coreutils 9.12-2 | Options | `df --human-readabel` → `df --human-readable` |
| `diff` | diffutils 3.12-2 | Options | `diff --unifide 'private operand' 'private operand'` → `diff --unified 'private operand' 'private operand'` |
| `dirname` | coreutils 9.12-2 | Options | `dirname --zeor 'private operand'` → `dirname --zero 'private operand'` |
| `dmesg` | util-linux 2.42.4-1 | Options | `dmesg --humna` → `dmesg --human` |
| `du` | coreutils 9.12-2 | Options | `du --human-readabel` → `du --human-readable` |
| `envsubst` | gettext 1.0-2 | Options | `envsubst --variablse` → `envsubst --variables` |
| `eza` | eza 0.23.5-2 | Options | `eza --logn` → `eza --long` |
| `fastfetch` | fastfetch 2.70.0-1 | Options | `fastfetch --list-logso` → `fastfetch --list-logos` |
| `fc-cache` | fontconfig 2:2.18.3-2 | Options | `fc-cache --verboes` → `fc-cache --verbose` |
| `fc-list` | fontconfig 2:2.18.3-2 | Options | `fc-list --verboes` → `fc-list --verbose` |
| `fd` | fd 10.5.0-3 | Options | `fd --hiddne` → `fd --hidden` |
| `ffmpeg` | ffmpeg 2:9.0.2-2 | Options | `ffmpeg -licenes` → `ffmpeg -license` |
| `ffprobe` | ffmpeg 2:9.0.2-2 | Options | `ffprobe -licenes` → `ffprobe -license` |
| `file` | file 5.48-1 | Options | `file --brife` → `file --brief` |
| `findmnt` | util-linux 2.42.4-1 | Options | `findmnt --bytse` → `findmnt --bytes` |
| `fmt` | coreutils 9.12-2 | Options | `fmt --crown-margni` → `fmt --crown-margin` |
| `fold` | coreutils 9.12-2 | Options | `fold --bytse` → `fold --bytes` |
| `free` | procps-ng 4.0.7-1 | Options | `free --bytse` → `free --bytes` |
| `fzf` | fzf 0.74.5-1 | Options | `fzf --mulit` → `fzf --multi` |
| `getfacl` | acl 2.4.0-1 | Options | `getfacl --accses` → `getfacl --access` |
| `gpg` | gnupg 2.4.9-3 | Options | `gpg --list-kesy` → `gpg --list-keys` |
| `grep` | grep 3.12-2 | Options | `grep --ignore-caes` → `grep --ignore-case` |
| `head` | coreutils 9.12-2 | Options | `head --linse 'private value'` → `head --lines 'private value'` |
| `hexdump` | util-linux 2.42.4-1 | Options | `hexdump --canonicla` → `hexdump --canonical` |
| `hostnamectl` | systemd 262.1-1 | Commands: `status`, `hostname` | `hostnamectl statsu` → `hostnamectl status` |
| `hyprctl` | hyprland 0.56.2-4 | Commands: `activewindow`, `activeworkspace`, `animations`, `binds`, `clients`, `configerrors`, `cursorpos`, `devices`, `globalshortcuts`, `instances`, `layers`, `layouts`, `splash`, `status`, `systeminfo`, `version`, `workspacerules`, `workspaces`, `monitors`, `getoption`, `decorations`, `reload` | `hyprctl activewindwo` → `hyprctl activewindow` |
| `iconv` | glibc 2.44+r50+g1848099f063e-1 | Options | `iconv --lits` → `iconv --list` |
| `id` | coreutils 9.12-2 | Options | `id --usre` → `id --user` |
| `info` | texinfo 7.3-3 | Options | `info --apropso 'private value'` → `info --apropos 'private value'` |
| `join` | coreutils 9.12-2 | Options | `join --ignore-caes 'private operand' 'private operand'` → `join --ignore-case 'private operand' 'private operand'` |
| `lazygit` | lazygit 0.66.2-1 | Options | `lazygit --paht 'private value'` → `lazygit --path 'private value'` |
| `limine` | limine 12.9.4-1 | Commands: `help`, `version` | `limine hepl` → `limine help` |
| `localectl` | systemd 262.1-1 | Commands: `status`, `list-locales`, `list-keymaps`, `list-x11-keymap-models`, `list-x11-keymap-layouts`, `list-x11-keymap-variants`, `list-x11-keymap-options` | `localectl statsu` → `localectl status` |
| `loginctl` | systemd 262.1-1 | Commands: `list-sessions`, `list-users`, `list-seats`, `session-status`, `user-status`, `seat-status`, `show-session`, `show-user`, `show-seat` | `loginctl list-sessiosn` → `loginctl list-sessions` |
| `ls` | coreutils 9.12-2 | Options | `ls --almost-lal` → `ls --almost-all` |
| `lsblk` | util-linux 2.42.4-1 | Options | `lsblk --bytse` → `lsblk --bytes` |
| `lscpu` | util-linux 2.42.4-1 | Options | `lscpu --onlien` → `lscpu --online` |
| `make` | make 4.4.1-3 | Options | `make --directoyr 'private value'` → `make --directory 'private value'` |
| `man` | man-db 2.13.1-2 | Options | `man --apropso` → `man --apropos` |
| `md5sum` | coreutils 9.12-2 | Options | `md5sum --chekc` → `md5sum --check` |
| `mkdir` | coreutils 9.12-2 | Options | `mkdir --parenst 'private operand'` → `mkdir --parents 'private operand'` |
| `mkinitcpio` | limine-mkinitcpio-hook 1.40.0-2 | Options | `mkinitcpio --listhoosk` → `mkinitcpio --listhooks` |
| `mpv` | mpv 1:0.41.0-6 | Options | `mpv --fullscrene` → `mpv --fullscreen` |
| `mv` | coreutils 9.12-2 | Options | `mv --verboes 'private operand' 'private operand'` → `mv --verbose 'private operand' 'private operand'` |
| `networkctl` | systemd 262.1-1 | Commands: `list`, `lldp`, `status` | `networkctl lits` → `networkctl list` |
| `nl` | coreutils 9.12-2 | Options | `nl --body-numberign 'private value'` → `nl --body-numbering 'private value'` |
| `nm` | binutils 2.47-4 | Options | `nm --demangel` → `nm --demangle` |
| `notify-send` | libnotify 0.8.9-1 | Options | `notify-send --urgenyc 'private value'` → `notify-send --urgency 'private value'` |
| `objdump` | binutils 2.47-4 | Options | `objdump --all-headesr` → `objdump --all-headers` |
| `od` | coreutils 9.12-2 | Options | `od --address-radxi 'private value'` → `od --address-radix 'private value'` |
| `openssl` | openssl 3.6.5-1 | Commands: `version`, `list`, `ciphers`, `dgst`, `sha256`, `sha512`, `verify`, `x509` | `openssl versino` → `openssl version` |
| `pacman` | pacman 7.1.0.r9.g54d9411-3 | Options | `pacman --queyr` → `pacman --query` |
| `pamixer` | pamixer 1.6-4 | Options | `pamixer --get-voluem` → `pamixer --get-volume` |
| `paste` | coreutils 9.12-2 | Options | `paste --delimitesr 'private value'` → `paste --delimiters 'private value'` |
| `pkg-config` | pkgconf 3.0.10-1 | Options | `pkg-config --modversino` → `pkg-config --modversion` |
| `printenv` | coreutils 9.12-2 | Options | `printenv --nlul` → `printenv --null` |
| `qpdf` | qpdf 12.4.2-1 | Options | `qpdf --chekc` → `qpdf --check` |
| `readlink` | coreutils 9.12-2 | Options | `readlink --canonicaliez 'private operand'` → `readlink --canonicalize 'private operand'` |
| `realpath` | coreutils 9.12-2 | Options | `realpath --canonicaliez 'private operand'` → `realpath --canonicalize 'private operand'` |
| `rev` | util-linux 2.42.4-1 | Options | `rev --zeor` → `rev --zero` |
| `rg` | ripgrep 15.2.0-1 | Options | `rg --ignore-caes` → `rg --ignore-case` |
| `rmdir` | coreutils 9.12-2 | Options | `rmdir --parenst 'private operand'` → `rmdir --parents 'private operand'` |
| `rsync` | rsync 3.5.1-3 | Options | `rsync --archiev` → `rsync --archive` |
| `rustc` | rustc 1.99.1 (58cf8f9c3 2026-10-13) | Options | `rustc --explani 'private value'` → `rustc --explain 'private value'` |
| `rustfmt` | rustfmt 1.10.0-stable (58cf8f9c35 2026-10-13) | Options | `rustfmt --chekc` → `rustfmt --check` |
| `seq` | coreutils 9.12-2 | Options | `seq --equal-widht` → `seq --equal-width` |
| `sha256sum` | coreutils 9.12-2 | Options | `sha256sum --chekc` → `sha256sum --check` |
| `sha512sum` | coreutils 9.12-2 | Options | `sha512sum --chekc` → `sha512sum --check` |
| `shuf` | coreutils 9.12-2 | Options | `shuf --ecoh` → `shuf --echo` |
| `sort` | coreutils 9.12-2 | Options | `sort --reveres` → `sort --reverse` |
| `split` | coreutils 9.12-2 | Options | `split --bytse 'private value'` → `split --bytes 'private value'` |
| `ss` | iproute2 7.3.0-1 | Options | `ss --listenign` → `ss --listening` |
| `stat` | coreutils 9.12-2 | Options | `stat --file-systme 'private operand'` → `stat --file-system 'private operand'` |
| `strings` | binutils 2.47-4 | Options | `strings --print-file-naem` → `strings --print-file-name` |
| `systemd-analyze` | systemd 262.1-1 | Commands: `time`, `blame`, `critical-chain`, `plot`, `unit-paths`, `syscall-filter`, `security`, `calendar`, `timespan` | `systemd-analyze tiem` → `systemd-analyze time` |
| `tac` | coreutils 9.12-2 | Options | `tac --befoer` → `tac --before` |
| `tail` | coreutils 9.12-2 | Options | `tail --linse 'private value'` → `tail --lines 'private value'` |
| `tee` | coreutils 9.12-2 | Options | `tee --appedn` → `tee --append` |
| `timedatectl` | systemd 262.1-1 | Commands: `status`, `timesync-status`, `show`, `show-timesync`, `list-timezones` | `timedatectl statsu` → `timedatectl status` |
| `tldr` | tldr 3.4.4-1 | Options | `tldr --lits` → `tldr --list` |
| `touch` | coreutils 9.12-2 | Options | `touch --no-creaet 'private operand'` → `touch --no-create 'private operand'` |
| `uname` | coreutils 9.12-2 | Options | `uname --kernel-naem` → `uname --kernel-name` |
| `uniq` | coreutils 9.12-2 | Options | `uniq --coutn` → `uniq --count` |
| `uptime` | procps-ng 4.0.7-1 | Options | `uptime --pretyt` → `uptime --pretty` |
| `watch` | procps-ng 4.0.7-1 | Options | `watch --intervla 'private value'` → `watch --interval 'private value'` |
| `wc` | coreutils 9.12-2 | Options | `wc --bytse` → `wc --bytes` |
| `who` | coreutils 9.12-2 | Options | `who --coutn` → `who --count` |
| `wl-copy` | wl-clipboard 1:2.3.0-1 | Options | `wl-copy --paste-onec` → `wl-copy --paste-once` |
| `wl-paste` | wl-clipboard 1:2.3.0-1 | Options | `wl-paste --no-newlien` → `wl-paste --no-newline` |
| `wpctl` | wireplumber 0.5.18-1 | Commands: `status`, `list`, `get-volume`, `inspect`, `set-default`, `set-volume`, `set-mute`, `set-profile`, `set-route` | `wpctl statsu` → `wpctl status` |
| `xdg-open` | xdg-utils 1.2.1-2 | Options | `xdg-open --manula` → `xdg-open --manual` |
| `yay` | yay 13.0.1-1 | Options | `yay --queyr` → `yay --query` |
| `yt-dlp` | yt-dlp 2026.08.19-1 | Options | `yt-dlp --list-formast` → `yt-dlp --list-formats` |

## Remaining top-priority work

This batch covered fourteen of the 21 top-priority names. The subsequent
[nested CLI batch](NESTED_CLI_BATCH.md) adds Nix, iwctl, Zellij, and strace.
Eighteen now have scoped adapters; these three remain planned:

| Tool | Remaining work |
|---|---|
| crontab | Primarily short flags and impactful edit/remove semantics; no confident correction rule yet |
| ssh-keygen | Primarily short flags whose one-letter differences select very different key operations |
| lsof | Dense short-option syntax; no useful reviewed long-option correction set in this installed version |

Other roadmap gaps include containerd/Podman/Kubernetes clients, Docker buildx,
additional package managers, nested cloud/deployment CLIs, shell builtins and
wrappers, and the remaining desktop/developer utilities. Unavailable tools such
as htop, hyperfine, ninja, pandoc, reflector, tree and wget were not silently
marked tested. They need their own fixtures and meaningful positive/negative
cases before entering the active registry.
