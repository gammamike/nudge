# Linux command expansion

Checked on Linux x86_64 on 2026-11-01. This expansion adds **147 executable
adapters**, increasing the registry from 120 to **267**, and extends the existing
Docker adapter with Buildx inspection commands. These are scoped corrections,
not complete coverage of every CLI or every requested tool. See the
[remaining inventory](CLI_STATUS.md).

## Batches

Each batch passed fixture tests and metadata-only checks against real installed
or temporarily extracted Linux executables before the next batch was added.
No proposed command, package installation, service operation, or live model
request was executed by these checks.

| Batch | New executables | Names |
|---|---:|---|
| 1. files archives wrappers | 19 | `awk`, `bunzip2`, `bzip2`, `env`, `gunzip`, `gzip`, `hostname`, `less`, `ln`, `mktemp`, `more`, `nice`, `sed`, `tar`, `timeout`, `tr`, `unxz`, `which`, `xz` |
| 2. system inspection networking | 18 | `blkid`, `busctl`, `fdisk`, `fuser`, `gsettings`, `ldd`, `lsusb`, `modprobe`, `nvidia-smi`, `pgrep`, `ps`, `resolvectl`, `sysctl`, `tailscale`, `udevadm`, `upower`, `vmstat`, `wg` |
| 3. developer data | 12 | `jq`, `luarocks`, `node`, `npm`, `pg_dump`, `pg_restore`, `pip`, `pip3`, `psql`, `ruby`, `rustup`, `sqlite3` |
| 4. desktop modern utilities | 19 | `awww`, `btm`, `delta`, `duf`, `dust`, `hyperfine`, `hypridle`, `hyprlock`, `hyprpaper`, `lsd`, `mako`, `makoctl`, `playerctl`, `procs`, `sd`, `tokei`, `tree`, `walker`, `waybar` |
| 5. containers orchestration | 9 | `buildah`, `ctr`, `docker-compose`, `helm`, `kubectl`, `kustomize`, `nerdctl`, `podman`, `skopeo` |
| 6. utilities editors | 14 | `inotifywait`, `lazydocker`, `locate`, `lsmod`, `makepkg`, `nvim`, `paccache`, `patch`, `python`, `python3`, `sensors`, `top`, `vim`, `whois` |
| 7. developer nested | 5 | `deno`, `gh`, `starship`, `uv`, `zoxide` |
| 8. administration inspection | 10 | `cryptsetup`, `efibootmgr`, `getent`, `mount`, `parted`, `rename`, `snapper`, `sync`, `ufw`, `visudo` |
| 9. network diagnostics editors | 17 | `dmidecode`, `ethtool`, `gdb`, `glow`, `htop`, `http`, `iostat`, `lshw`, `ltrace`, `micro`, `mtr`, `nano`, `nmap`, `screen`, `smartctl`, `tcpdump`, `wget` |
| 10. build data security | 12 | `age`, `aria2c`, `black`, `cmake`, `dracut`, `just`, `mypy`, `ninja`, `pandoc`, `pytest`, `sops`, `stow` |
| 11. project tooling | 5 | `atuin`, `chezmoi`, `meson`, `pre-commit`, `ruff` |
| 12. media and environment | 7 | `cpupower`, `direnv`, `git-lfs`, `magick`, `sox`, `swapon`, `virtualenv` |

Docker Buildx supports `ls`, `inspect`, `du`, and `version`. Creation, removal,
build execution, and `inspect --bootstrap` are excluded. Buildx's own version is
included in its metadata cache key.

## Correction boundaries

- Flat profiles correct reviewed options. Command profiles also correct their
  listed command words. Installed help must advertise the candidate.
- New generic nested profiles use unique local one-edit corrections only. They
  do not send unknown extensions, command names, or operands to a model. Existing
  eligible adapters retain optional Codex, Claude Code, and local LLM selection.
  The new `magick`, `cpupower`, `direnv`, and `git-lfs` command profiles are also
  local-only. `--force-ai` does not override these adapter boundaries.
- Kubectl global options come from its separate `options` metadata. Installed
  `kubectl-NAME` executables prevent rewriting that root command name. Podman and
  other reviewed aliases are checked against parent or leaf help before use.
- Argument values, file paths, URLs, namespaces, selectors, and command payloads
  remain unchanged. This is a reviewed grammar, not semantic validation of every
  value, resource, or option combination.
- Some tools require an inspection/dry-run mode. Such a mode must be parsed as an
  actual option: an option value or filename named `--dry-run` does not count.
- Many destructive, write-output, privilege-changing, configuration-loading, and
  arbitrary-execution forms remain excluded. Explicit user commands and existing
  tool configuration can still have normal side effects when accepted.
- Bash aliases/functions, builtins, executable spelling corrections, shell
  expansions, pipelines, and interactive application keystrokes remain outside
  this implementation. Only Linux and interactive Bash 5+ are supported.
- The tested `swww` repository package provides `awww`. That executable has its
  own adapter; the legacy `swww` name is not silently treated as supported.

## Exact scope and evidence

The tables list canonical command routes or reviewed long options. Short options,
value arity, operand limits, and options specific to a route are defined in the
[flat registry](../data/linux-profiles.json) and
[nested registry](../data/nested-profiles.json). An entry below does not permit
all options supported by that executable. Some declared flags may be absent in
other installed versions; absent flags are not candidates.

[Positive and negative cases](../tests/fixtures/expansion-cases.json),
[package/version provenance](../tests/fixtures/expansion-provenance.json), and
captured [flat](../tests/fixtures/linux-profile-help.json) and
[nested](../tests/fixtures/nested-cli-help.json) help are retained in the repository.
Package archive provenance includes runtime dependencies, not additional adapters.

| Executable | Reviewed scope | Required mode / payload boundary | Example input |
|---|---|---|---|
| `age` | Options: --help, --version, --encrypt, --decrypt, --armor, --recipient, --recipients-file, --identity | Requires --encrypt, -e, --decrypt, -d | `age --decrpyt -i "key file" example.age` |
| `aria2c` | Options: --help, --version, --show-files, --no-conf | Requires --show-files, -S | `aria2c --show-fiels example.torrent` |
| `atuin` | Commands: status, stats, search, history list | Reviewed route-specific flags; local corrections only | `atuin history lsit --cmd-only` |
| `awk` | Options: --help, --version, --field-separator, --assign, --file, --source, --posix, --traditional, --sandbox, --characters-as-bytes, --lint | arguments after first operand are opaque | `awk --field-separtaor : -f program.awk input.txt` |
| `awww` | Commands: query, restore, pause, unpause | Literal operands; reviewed flags only | `awww qurey` |
| `black` | Options: --help, --version, --check, --diff, --color, --no-color, --line-length, --target-version, --quiet, --verbose, --include, --exclude, --extend-exclude | Requires --check, --diff | `black --check --line-lenght 88 example.py` |
| `blkid` | Options: --help, --version, --output, --list-filesystems, --match-tag, --match-token, --label, --uuid, --probe, --info, --no-part-details | Literal operands; reviewed flags only | `blkid --list-filesystmes` |
| `btm` | Options: --help, --version, --basic, --expanded, --rate, --read_only, --tree, --battery, --disable_gpu, --theme, --celsius, --fahrenheit, --kelvin, --hide_avg_cpu | no positional arguments | `btm --read_onyl` |
| `buildah` | Commands: images, containers, inspect, info, version | Reviewed route-specific flags; local corrections only | `buildah contianers` |
| `bunzip2` | Options: --help, --version, --test, --stdout, --quiet, --verbose, --keep | Requires --test, -t, --stdout, -c, --list, -l | `bunzip2 --tset archive.bin` |
| `busctl` | Commands: list, tree, status, introspect, get-property | Literal operands; reviewed flags only | `busctl introspectt example.service /example` |
| `bzip2` | Options: --help, --version, --test, --stdout, --quiet, --verbose, --keep, --decompress | Requires --test, -t, --stdout, -c, --list, -l | `bzip2 --tset archive.bin` |
| `chezmoi` | Commands: status, diff, doctor, managed | Reviewed route-specific flags; local corrections only | `chezmoi stauts "example file"` |
| `cmake` | Options: --help, --version, --list-presets, --presets-file | Requires --list-presets; no positional arguments | `cmake --list-prsets=build` |
| `cryptsetup` | Commands: status, luksDump, luksUUID, isLuks | Literal operands; reviewed flags only | `cryptsetup stauts example` |
| `ctr` | Commands: images list, images check, containers list, containers info, namespaces list, tasks list, tasks ps, plugins list, version, info | Reviewed route-specific flags; local corrections only | `ctr images lsit` |
| `delta` | Options: --help, --version, --dark, --light, --line-numbers, --side-by-side, --syntax-theme, --paging, --width, --wrap-max-lines, --no-gitconfig, --color-only, --navigate, --list-languages, --list-syntax-themes | Literal operands; reviewed flags only | `delta --side-by-sdie a.txt b.txt` |
| `deno` | Commands: check, lint, info, doc, types | Reviewed route-specific flags; local corrections only | `deno chekc example.ts` |
| `dmidecode` | Options: --help, --version, --quiet, --string, --list-strings, --type, --list-types, --handle, --dump, --from-dump, --no-sysfs | no positional arguments | `dmidecode --list-stirngs` |
| `docker-compose` | Commands: ps, ls, logs, config, images, version | Reviewed route-specific flags; local corrections only | `docker-compose -f "compose file.yml" logs --tial 5 example` |
| `dracut` | Options: --help, --version, --list-modules, --printconfig, --print-cmdline, --quiet | Requires --list-modules, --printconfig, --print-cmdline; no positional arguments | `dracut --list-moduels` |
| `duf` | Options: -all, -inodes, -json, -hide, -hide-fs, -hide-mp, -only, -only-fs, -only-mp, -output, -sort, -style, -theme, -version, -warnings, -width | Literal operands; reviewed flags only | `duf -indoes` |
| `dust` | Options: --help, --version, --depth, --number-of-lines, --full-paths, --ignore-directory, --limit-filesystem, --apparent-size, --reverse, --no-colors, --no-percent-bars, --min-size, --filecount, --ignore-hidden, --filter, --file-types, --no-progress, --only-dir, --only-file, --output-format, --output-json | Literal operands; reviewed flags only | `dust --apparent-szie .` |
| `efibootmgr` | Options: --help, --version, --verbose, --quiet | no positional arguments | `efibootmgr --verbsoe` |
| `env` | Options: --help, --version, --ignore-environment, --null, --unset, --chdir, --debug | arguments after first operand are opaque | `env --ignore-environmetn printf --literal` |
| `ethtool` | Options: --help, --version, --statistics, --driver, --show-features, --show-offload | Literal operands; reviewed flags only | `ethtool --statistcis eth0` |
| `fdisk` | Options: --help, --version, --list, --list-details, --output, --bytes, --units | Requires --list, -l, --list-details, -x | `fdisk --list-detials /dev/example` |
| `fuser` | Options: --all, --inode, --mount, --ismountpoint, --namespace, --silent, --user, --verbose, --ipv4, --ipv6, --version, --list-signals | Literal operands; reviewed flags only | `fuser --verbsoe /tmp/example` |
| `gdb` | Options: --help, --version, --quiet, --silent, --nx, --nh, --batch, --batch-silent, --core, --exec, --se, --symbols, --directory, --readnow, --readnever, --nw, --tui | Literal operands; reviewed flags only | `gdb --batch --symobls example` |
| `getent` | Options: --help, --usage, --version, --no-addrconfig, --no-idn, --service, --verbose | Literal operands; reviewed flags only | `getent --no-adrrconfig hosts example.invalid` |
| `gh` | Commands: pr list, pr view, pr status, pr checks, issue list, issue view, repo view, repo list, run list, run view, release list, release view, auth status | Reviewed route-specific flags; local corrections only | `gh pr lsit --limit 5` |
| `glow` | Options: --help, --version, --all, --line-numbers, --preserve-new-lines, --style, --width | Literal operands; reviewed flags only | `glow --line-numebrs README.md` |
| `gsettings` | Commands: list-schemas, list-relocatable-schemas, list-keys, list-children, list-recursively, range, describe, get, writable, monitor | Literal operands; reviewed flags only | `gsettings list-schemsa` |
| `gunzip` | Options: --help, --version, --test, --stdout, --quiet, --verbose, --keep, --list | Requires --test, -t, --stdout, -c, --list, -l | `gunzip --tset archive.bin` |
| `gzip` | Options: --help, --version, --test, --stdout, --quiet, --verbose, --keep, --list, --decompress | Requires --test, -t, --stdout, -c, --list, -l | `gzip --tset archive.bin` |
| `helm` | Commands: list, status, history, lint, version, repo list, show chart, show values, show readme, show all | Reviewed route-specific flags; local corrections only | `helm hisotry example` |
| `hostname` | Options: --help, --version, --aliases, --domain, --fqdn, --long, --ip-addresses, --short | no positional arguments | `hostname --ip-addreses` |
| `htop` | Options: --help, --version, --no-color, --delay, --filter, --no-function-bar, --highlight-changes, --no-mouse, --no-meters, --max-iterations, --pid, --readonly, --sort-key, --tree, --user, --no-unicode | no positional arguments | `htop --readonyl --pid 123` |
| `http` | Options: --help, --version, --offline, --json, --form, --pretty, --style, --print, --headers, --body, --verbose, --ignore-stdin, --ignore-netrc | Requires --offline | `http --offline --prety=none GET example.invalid` |
| `hyperfine` | Options: --help, --version, --warmup, --min-runs, --max-runs, --runs, --style, --export-csv, --export-json, --export-markdown, --show-output, --command-name | Literal operands; reviewed flags only | `hyperfine --warmpu 1 "printf hello"` |
| `hypridle` | Options: --help, --version, --verbose, --quiet, --config | no positional arguments | `hypridle --verboes` |
| `hyprlock` | Options: --help, --version, --verbose, --quiet, --config, --immediate-render, --no-fade-in, --display | no positional arguments | `hyprlock --no-faed-in` |
| `hyprpaper` | Options: --help, --version, --verbose, --config | no positional arguments | `hyprpaper --conifg "wallpaper.conf"` |
| `inotifywait` | Options: --help, --monitor, --recursive, --quiet, --no-dereference, --exclude, --excludei, --include, --includei, --format, --timefmt, --csv, --timeout, --event, --no-newline | Literal operands; reviewed flags only | `inotifywait --recusrive "example dir"` |
| `iostat` | Options: --compact, --dec, --human, --pretty | Literal operands; reviewed flags only | `iostat --compcat -x 1 2` |
| `jq` | Options: --help, --version, --null-input, --raw-input, --slurp, --compact-output, --raw-output, --raw-output0, --join-output, --ascii-output, --sort-keys, --color-output, --monochrome-output, --tab, --indent, --unbuffered, --stream, --stream-errors, --seq, --from-file, --library-path, --exit-status | Literal operands; reviewed flags only | `jq --raw-outptu . data.json` |
| `just` | Options: --help, --version, --list, --summary, --dump, --show, --justfile, --working-directory, --color, --list-heading, --list-prefix, --unsorted, --no-aliases | Requires --list, -l, --summary, --dump, --show, -s | `just --lsit --unsorted` |
| `kubectl` | Commands: get, describe, logs, explain, api-resources, version, config current-context, config get-contexts, top node, top pod | Reviewed route-specific flags; local corrections only | `kubectl gte pods -n example` |
| `kustomize` | Commands: build, version | Reviewed route-specific flags; local corrections only | `kustomize biuld ./example` |
| `lazydocker` | Options: --help, --version, --config, --file, --project | no positional arguments | `lazydocker --proejct example` |
| `ldd` | Options: --help, --version, --unused, --verbose, --data-relocs, --function-relocs | Literal operands; reviewed flags only | `ldd --unuesd ./example` |
| `less` | Options: --help, --version, --ignore-case, --IGNORE-CASE, --LINE-NUMBERS, --line-numbers, --chop-long-lines, --quit-if-one-screen, --no-lessopen, --squeeze-blank-lines, --no-init, --RAW-CONTROL-CHARS | Literal operands; reviewed flags only | `less --chop-long-liens file` |
| `ln` | Options: --help, --version, --symbolic, --relative, --verbose, --no-dereference, --physical, --logical | Literal operands; reviewed flags only | `ln --symoblic source link` |
| `locate` | Options: --help, --version, --basename, --count, --database, --ignore-case, --limit, --null, --literal, --regexp, --regex, --wholename | Literal operands; reviewed flags only | `locate --ignore-csae example` |
| `lsd` | Options: --help, --version, --all, --almost-all, --color, --icon, --long, --oneline, --recursive, --tree, --depth, --directory-only, --permission, --size, --total-size, --date, --sort, --reverse, --group-dirs, --group-directories-first, --no-symlink, --ignore-glob, --inode, --header | Literal operands; reviewed flags only | `lsd --group-directoires-first .` |
| `lshw` | Options: -version, -html, -xml, -json, -short, -businfo, -class, -C, -c, -quiet, -sanitize, -numeric, -notime | no positional arguments | `lshw -santiize -json` |
| `lsmod` | Options: --help, --version, --verbose | no positional arguments | `lsmod --verbsoe` |
| `lsusb` | Options: --help, --version, --verbose, --tree | no positional arguments | `lsusb --verbsoe` |
| `ltrace` | Options: --help, --version, --align, --no-signals, --demangle, --library, --indent, --where | arguments after first operand are opaque | `ltrace --demanlge example --opaque-option` |
| `luarocks` | Commands: list, search, show, lint, which | Literal operands; reviewed flags only | `luarocks searhc example` |
| `makepkg` | Options: --help, --version, --packagelist, --printsrcinfo, --dir, --nocolor | Requires --packagelist, --printsrcinfo; no positional arguments | `makepkg --packagelist --nocolro` |
| `mako` | Options: --help, --config, --font, --background-color, --text-color, --width, --height, --margin, --padding, --border-size, --border-color, --default-timeout, --output, --anchor | no positional arguments | `mako --default-tiemout 3000` |
| `makoctl` | Commands: list, history, reload, restore, mode | Literal operands; reviewed flags only | `makoctl hisotry -j` |
| `meson` | Commands: introspect, configure | Reviewed route-specific flags; local corrections only | `meson introspect --targtes build` |
| `micro` | Options: -version, -config-dir | Literal operands; reviewed flags only | `micro -config-dri example file.txt` |
| `mktemp` | Options: --help, --version, --directory, --quiet, --suffix, --tmpdir | Literal operands; reviewed flags only | `mktemp --direcotry` |
| `modprobe` | Options: --help, --version, --resolve-alias, --show-depends, --showconfig, --show-config, --show-modversions, --dump-modversions, --show-exports, --verbose | Requires --resolve-alias, -R, --show-depends, -D, --showconfig, --show-config, -c, --show-modversions, --dump-modversions, --show-exports | `modprobe --show-depedns example_module` |
| `more` | Options: --help, --version, --silent, --logical, --no-pause, --print-over, --clean-print, --exit-on-eof, --squeeze, --plain, --lines | Literal operands; reviewed flags only | `more --exit-on-efo file` |
| `mount` | Options: --help, --version, --show-labels, --types | no positional arguments | `mount --show-lables` |
| `mtr` | Options: --help, --version, --report, --report-wide, --report-cycles, --json, --no-dns, --tcp, --udp, --interface, --address, --interval, --max-ttl | Literal operands; reviewed flags only | `mtr --report --report-cylces 5 example.invalid` |
| `mypy` | Options: --help, --version, --verbose, --strict, --check-untyped-defs, --warn-unused-ignores, --show-error-codes, --show-column-numbers, --no-error-summary, --pretty, --no-incremental, --python-version, --ignore-missing-imports | Literal operands; reviewed flags only | `mypy --strcit example.py` |
| `nano` | Options: --help, --version, --ignorercfiles, --restricted, --view, --linenumbers, --softwrap, --tabsize, --tabstospaces, --mouse, --constantshow, --noconvert, --nonewlines, --backup | Literal operands; reviewed flags only | `nano --linenubmers example.txt` |
| `nerdctl` | Commands: ps, images, inspect, logs, info, version, image ls, image inspect, image history, container ls, container inspect, network ls, network inspect, volume ls, volume inspect | Reviewed route-specific flags; local corrections only | `nerdctl contianer ls` |
| `nice` | Options: --help, --version, --adjustment | arguments after first operand are opaque | `nice --adjustmetn 5 printf --literal` |
| `ninja` | Options: --version, --verbose, --quiet | Requires -n | `ninja  -n --verbsoe example` |
| `nmap` | Options: --help, --version, --reason, --open, --top-ports, --exclude, --exclude-ports | Literal operands; reviewed flags only | `nmap --reasno --top-ports 5 example.invalid` |
| `node` | Options: --help, --version, --check, --trace-warnings, --no-warnings, --enable-source-maps, --unhandled-rejections | arguments after first operand are opaque | `node --trace-warnigns script.js --literal` |
| `npm` | Commands: outdated, ci, test, prefix, root, whoami, doctor, install, search, view, ls, explain, run | Literal operands; reviewed flags only | `npm outdaetd` |
| `nvidia-smi` | Options: --help, -h, --version, --query, -q, --list-gpus, -L, --id, -i, --query-gpu, --format, --loop, -l, --loop-ms, -lms, --xml-format, -x | no positional arguments | `nvidia-smi --query-gup=name --format=csv` |
| `nvim` | Options: --help, --version, --clean, --api-info | Literal operands; reviewed flags only | `nvim --claen "example file"` |
| `paccache` | Options: --help, --version, --dryrun, --arch, --cachedir, --ignore, --keep, --min-atime, --min-mtime, --nocolor, --null, --quiet, --uninstalled, --verbose | Requires --dryrun, -d | `paccache --dryrun --uninstaled` |
| `pandoc` | Options: --help, --version, --from, --read, --to, --write, --standalone, --wrap, --ascii, --toc, --table-of-contents, --toc-depth, --number-sections, --strip-comments, --markdown-headings, --quiet | Literal operands; reviewed flags only | `pandoc --standlaone --from markdown --to html example.md` |
| `parted` | Options: --help, --version, --list, --machine, --json | Requires --list, -l; no positional arguments | `parted --list --machien` |
| `patch` | Options: --help, --version, --dry-run, --strip, --fuzz, --ignore-whitespace, --context, --normal, --unified, --forward, --reverse, --input, --quiet, --silent, --verbose, --posix, --directory, --binary | Requires --dry-run | `patch --dry-run --verbsoe -i "example patch"` |
| `pg_dump` | Options: --help, --version, --dbname, --host, --port, --username, --no-password, --password, --schema-only, --data-only, --schema, --table, --format, --file, --verbose, --no-owner, --no-privileges | Literal operands; reviewed flags only | `pg_dump --schema-onyl example` |
| `pg_restore` | Options: --help, --version, --list, --format, --verbose | Requires --list, -l | `pg_restore --lsit archive.dump` |
| `pgrep` | Options: --help, --version, --delimiter, --list-name, --list-full, --count, --full, --ignore-case, --newest, --oldest, --parent, --euid, --uid, --exact, --pidfile, --ignore-ancestors | Literal operands; reviewed flags only | `pgrep --list-fll bash` |
| `pip` | Commands: list, show, freeze, check, inspect, install, download | Literal operands; reviewed flags only | `pip list --outdaetd` |
| `pip3` | Commands: list, show, freeze, check, inspect, install, download | Literal operands; reviewed flags only | `pip3 list --outdaetd` |
| `playerctl` | Commands: play, pause, play-pause, stop, next, previous, status, metadata, position, volume, loop, shuffle, open | Literal operands; reviewed flags only | `playerctl play-pasue` |
| `podman` | Commands: ps, images, inspect, logs, info, version, image inspect, image history, image list, container inspect, container list, network ls, network inspect, volume ls, volume inspect | Reviewed route-specific flags; local corrections only | `podman contianer ls` |
| `pre-commit` | Commands: validate-config, validate-manifest, sample-config | Reviewed route-specific flags; local corrections only | `pre-commit validate-conifg example.yaml` |
| `procs` | Options: --help, --version, --text, --regex, --smart, --and, --or, --list, --thread, --tree, --watch, --watch-interval, --only, --sorta, --sortd, --color, --theme, --json, --no-header | Literal operands; reviewed flags only | `procs --thraed` |
| `ps` | Options: --help, --version, --forest, --sort, --pid, --ppid, --user, --User, --format, --no-headers, --headers, --width, --rows | no positional arguments | `ps --forst -ef` |
| `psql` | Options: --help, --version, --dbname, --host, --port, --username, --no-password, --password, --no-psqlrc, --list, --command, --file, --quiet, --echo-errors, --no-align, --csv, --field-separator, --tuples-only, --expanded | Literal operands; reviewed flags only | `psql --tuples-onyl --dbname example --command "select 1"` |
| `pytest` | Options: --help, --version, --collect-only, --co, --quiet, --verbose, --exitfirst, --maxfail, --strict-config, --strict-markers, --strict, --capture, --no-header, --no-summary, --disable-warnings | Literal operands; reviewed flags only | `pytest --collect-onyl example.py` |
| `python` | Options: --help, --version, --check-hash-based-pycs | arguments after first operand are opaque | `python --check-hash-based-pyc=always -B example.py --private-argument` |
| `python3` | Options: --help, --version, --check-hash-based-pycs | arguments after first operand are opaque | `python3 --check-hash-based-pyc=always -B example.py --private-argument` |
| `rename` | Options: --help, --version, --verbose, --no-act, --all, --last, --no-overwrite, --interactive | Requires --no-act, -n | `rename --no-act --verbsoe old new example` |
| `resolvectl` | Commands: status, statistics, query, monitor, show-cache, show-server-state | Literal operands; reviewed flags only | `resolvectl statistcis` |
| `ruby` | Options: --help, --version, --debug, --encoding, --external-encoding, --internal-encoding, --backtrace-limit, --verbose | arguments after first operand are opaque | `ruby --backtrace-limt 10 app.rb --literal` |
| `ruff` | Commands: check, rule, linter | Reviewed route-specific flags; local corrections only | `ruff chekc --no-fix example.py` |
| `rustup` | Commands: show, check, which | Literal operands; reviewed flags only | `rustup shwo` |
| `screen` | Options: -list, -ls, -q, -v, -h, -S, -t | Requires -list, -ls | `screen -lsit` |
| `sd` | Options: --help, --version, --preview, --fixed-strings, --max-replacements, --flags, --across | Requires --preview, -p | `sd --preveiw "old text" "new text" file` |
| `sed` | Options: --help, --version, --quiet, --silent, --expression, --file, --regexp-extended, --sandbox, --unbuffered, --null-data, --separate | Literal operands; reviewed flags only | `sed --regexp-exteneded -e s/a/b/ input.txt` |
| `sensors` | Options: --help, --version, --config-file, --fahrenheit, --no-adapter, --bus-list, --allow-no-sensors | Literal operands; reviewed flags only | `sensors --fahrenhiet` |
| `skopeo` | Commands: inspect, list-tags, manifest-digest | Reviewed route-specific flags; local corrections only | `skopeo inspcet docker://example.invalid/image` |
| `smartctl` | Options: --help, --version, --all, --info, --health, --attributes, --log, --device, --json | Literal operands; reviewed flags only | `smartctl --attribtues /dev/example` |
| `snapper` | Commands: list, list-configs, get-config, status, diff, xadiff | Literal operands; reviewed flags only | `snapper --config root lsit --columns number` |
| `sops` | Options: --help, --version, --decrypt, --encrypt, --input-type, --output-type, --extract, --indent | Requires --decrypt, -d, --encrypt, -e | `sops --decrypt --output-tyep json example.yaml` |
| `sqlite3` | Options: -help, -version, -readonly, -safe, -noinit, -batch, -bail, -box, -column, -csv, -echo, -html, -json, -line, -list, -markdown, -quote, -separator, -nullvalue, -table, -tabs | Requires -readonly; arguments after first operand are opaque | `sqlite3 -readonyl -json database.db` |
| `starship` | Commands: print-config, preset | Reviewed route-specific flags; local corrections only | `starship print-conifg --default` |
| `stow` | Options: --help, --version, --dir, --target, --ignore, --dotfiles, --no, --simulate, --verbose | Requires --no, -n, --simulate | `stow --simulate --dotfiels example` |
| `sync` | Options: --help, --version, --data, --file-system | Literal operands; reviewed flags only | `sync --file-sysetm example` |
| `sysctl` | Options: --help, --version, --all, --names, --values, --pattern, --binary | no positional arguments | `sysctl --vaues --all` |
| `tailscale` | Commands: status, ip, netcheck, ping, version, whois | Literal operands; reviewed flags only | `tailscale statsu --json` |
| `tar` | Options: --help, --version, --list, --file, --verbose, --gzip, --bzip2, --xz, --numeric-owner, --full-time, --show-transformed-names | Requires --list, -t | `tar --lsit --file archive.tar` |
| `tcpdump` | Options: --help, --version, --immediate-mode, --count, --number, --print, --micro, --nano, --time-stamp-precision | Literal operands; reviewed flags only | `tcpdump --immediate-mdoe -c 5 -i eth0` |
| `timeout` | Options: --help, --version, --preserve-status, --foreground, --verbose, --signal, --kill-after | arguments after first operand are opaque | `timeout --preserve-sttaus 5 printf --literal` |
| `tokei` | Options: --help, --version, --columns, --exclude, --files, --hidden, --languages, --no-ignore, --no-ignore-parent, --no-ignore-dot, --no-ignore-vcs, --output, --sort, --rsort, --types, --compact, --num-format, --verbose | Literal operands; reviewed flags only | `tokei --langauges` |
| `top` | Options: --help, --version, --apply-defaults, --batch-mode, --delay, --threads-show, --iterations, --list-fields, --sort-override, --pid, --secure-mode, --filter-any-user, --filter-only-euser, --width | no positional arguments | `top --batch-mdoe --iterations 1` |
| `tr` | Options: --help, --version, --complement, --delete, --squeeze-repeats, --truncate-set1 | Literal operands; reviewed flags only | `tr --squeeze-repeast x` |
| `tree` | Options: --help, --version, --gitignore, --ignore-case, --matchdirs, --prune, --noreport, --filelimit, --du, --inodes, --device, --dirsfirst, --filesfirst, --sort, --charset, --timefmt | Literal operands; reviewed flags only | `tree --dirsfrist -L 2 .` |
| `udevadm` | Commands: info, cat | Literal operands; reviewed flags only | `udevadm info --attribute-wlak /dev/example` |
| `ufw` | Commands: status, show, version | Literal operands; reviewed flags only | `ufw stauts verbose` |
| `unxz` | Options: --help, --version, --test, --stdout, --quiet, --verbose, --keep, --list | Requires --test, -t, --stdout, -c, --list, -l | `unxz --tset archive.bin` |
| `upower` | Options: --help, --version, --battery, --dump, --enumerate, --monitor, --monitor-detail, --show-info | no positional arguments | `upower --enumreate` |
| `uv` | Commands: tree, audit, pip list, pip show, pip freeze, pip check, python list, python find, tool list, cache dir | Reviewed route-specific flags; local corrections only | `uv pip lsit --format=json` |
| `vim` | Options: --help, --version, --clean, --noplugin | Literal operands; reviewed flags only | `vim --claen "example file"` |
| `visudo` | Options: --help, --version, --check, --file, --quiet, --strict | Requires --check, -c; no positional arguments | `visudo --check --strcit --file example` |
| `vmstat` | Options: --help, --version, --active, --forks, --slabs, --one-header, --stats, --disk, --disk-sum, --partition, --unit, --wide, --timestamp, --no-first | Literal operands; reviewed flags only | `vmstat --timeestamp 1 2` |
| `walker` | Options: --help, --version, --nosearch, --nohints, --inputonly, --index, --provider, --set, --placeholder, --height, --width, --theme, --dmenu | no positional arguments | `walker --placehodler "Search apps"` |
| `waybar` | Options: --help, --version, --config, --style, --log-level, --bar | no positional arguments | `waybar --log-levle debug` |
| `wg` | Commands: show | Literal operands; reviewed flags only | `wg shwo example` |
| `wget` | Options: --help, --version, --spider, --quiet, --verbose, --server-response, --timeout, --tries, --no-config, --no-netrc | Requires --spider | `wget --spider --server-resposne https://example.invalid` |
| `which` | Options: --help, --version, --all, --skip-dot, --skip-tilde, --show-dot, --show-tilde, --skip-alias, --skip-functions | Literal operands; reviewed flags only | `which --skip-tidle bash` |
| `whois` | Options: --help, --version, --host, --port, --verbose, --no-recursion | Literal operands; reviewed flags only | `whois --no-recusrion example.invalid` |
| `xz` | Options: --help, --version, --test, --stdout, --quiet, --verbose, --keep, --list, --decompress | Requires --test, -t, --stdout, -c, --list, -l | `xz --tset archive.bin` |
| `zoxide` | Commands: query | Reviewed route-specific flags; local corrections only | `zoxide qeury --list "example dir"` |
| `cpupower` | Commands: frequency-info, idle-info, powercap-info, info | Local corrections only | `cpupower frequency-ifno` |
| `direnv` | Commands: status, version, stdlib | Local corrections only | `direnv stauts --json` |
| `git-lfs` | Commands: status, env, version, ls-files | Local corrections only | `git-lfs stauts` |
| `magick` | Commands: identify | Local corrections only | `magick identify -verbsoe "example image.png"` |
| `sox` | Options: --help, --version, --info, --i | Requires --info, --i | `sox --inof "audio file.wav"` |
| `swapon` | Options: --help, --version, --show, --output-all, --noheadings, --raw, --bytes, --summary | Requires --show, --summary, -s; no positional arguments | `swapon --show --noheadigns` |
| `virtualenv` | Options: --help, --version, --with-traceback, --read-only-app-data, --no-vcs-ignore, --system-site-packages, --symlinks, --copies, --always-copy, --no-seed, --without-pip, --no-download, --never-download, --no-pip, --no-setuptools, --no-periodic-update, --prompt, --python, --quiet, --verbose | Exactly one destination; clearing excluded | `virtualenv --system-site-packgaes --no-download "example venv"` |

## Validation

All 12 batches passed their focused tests. The complete suite passed **11 Rust
unit tests and 77 integration tests**, including the existing 1,823 catalog
regression cases. The integration suite includes positive correction, correctly
spelled runtime failure, missing metadata, and excluded-operation cases for each
new executable; Bash PTY cancellation/acceptance for one representative per
batch; Kubectl plugin/global-option and forced-provider boundary checks; and Codex, Claude Code, and local LLM
mock regressions. No accepted operation runs against a real target executable.

Formatting, Clippy with warnings denied, release build, and Bash syntax checks
passed. A Rust 1.88.0 static musl build also passed installer lifecycle tests in
isolated Ubuntu, Debian, Fedora, and Alpine userspaces; see the
[distribution recheck](DISTRIBUTION_TESTS.md#command-expansion-recheck). Local LLM tests use loopback mock servers and need permission to bind a
local socket. Hosted CI has not run for this expansion until it is pushed.

Reproduce after building the release binary:

```bash
python3 -m unittest discover -s tests -v
python3 tests/collect_nested_help.py --tool kubectl --output /tmp/kubectl-help.json
python3 tests/benchmark_expansion.py --samples 25 --output /tmp/expansion-benchmark.json
```

The benchmark requires its representative tools on PATH; missing metadata fails
rather than generating fabricated timings. Extracted packages may need their
runtime library/module paths. These timings measure local suggestion generation,
not the original command, confirmation, or a model request. Each row used one
fresh-cache lookup and 25 warm samples; they are development measurements, not a
cross-machine latency guarantee.

| Input | Cold engine ms | Warm engine median ms | Warm process wall median ms |
|---|---:|---:|---:|
| `age --decrpyt -i "key file" example.age` | 2.938 | 0.580 | 1.636 |
| `atuin history lsit --cmd-only` | 13.622 | 0.870 | 2.148 |
| `awk --field-separtaor : -f program.awk input.txt` | 2.856 | 0.489 | 1.602 |
| `awww qurey` | 2.515 | 0.445 | 1.498 |
| `blkid --list-filesystmes` | 2.579 | 0.560 | 1.608 |
| `buildah contianers` | 43.941 | 0.757 | 1.989 |
| `cpupower frequency-ifno` | 19.426 | 0.487 | 1.527 |
| `cryptsetup stauts example` | 3.507 | 1.030 | 2.074 |
| `deno chekc example.ts` | 9.155 | 0.738 | 1.920 |
| `dmidecode --list-stirngs` | 2.700 | 0.469 | 1.488 |
| `inotifywait --recusrive "example dir"` | 3.034 | 0.644 | 1.689 |
| `jq --raw-outptu . data.json` | 2.622 | 0.646 | 1.706 |

[Raw measurements](../tests/fixtures/expansion-benchmark.json).
