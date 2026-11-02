# Nix, iwctl, Zellij, and strace

Implemented and checked on Linux on 2026-11-01. These four adapters bring the
registry to **120 executable names** and top-priority coverage to **18 of 21**.
The executable must be spelled correctly and installed. Support is scoped to
reviewed syntax; it does not diagnose permissions, connection failures, missing
packages, devices, sessions, or processes.

This report records the original four-tool batch. The
[latest expansion](CLI_EXPANSION.md) documents subsequent additions.

## Supported forms

| Executable | Reviewed command forms | Boundaries |
|---|---|---|
| `nix` | `build`, `eval`, `search`, `path-info`, `develop`, `run`, `shell`, `env shell`; `flake show/metadata/check/update/lock`; `profile list/history/diff-closures`; `store info/ls/cat/diff-closures` | Nested command words and reviewed long options. Global options retain their values. Two-value options such as `--argstr` and `--override-input` preserve both arguments. `-c`/`--command` payloads and `run -- …` are opaque. No automatic enabling of experimental features, config changes, store deletion/repair, profile removal, or legacy `nix-*` executable adapters. |
| `iwctl` | `adapter/device/known-networks list`, selector + `show`; `station list`, selector + `show/scan/connect/connect-hidden/disconnect/get-networks/get-hidden-access-points/get-bsses` | Correct group/action words while retaining interface IDs, adapter names, SSIDs, credentials, and other values. Root options precede the group. An incomplete selector is never sent to a model; a one-edit `list` typo is local-only. No property editing, forgetting saved networks, AP, WSC, or provisioning operations. |
| `zellij` | `list-sessions`, `list-aliases`, `attach`, `run`, `setup`; nested actions listed below | Recognizes reviewed installed aliases. Root and subcommand options have separate scopes. Session names and pane/tab names are preserved. `run` requires `-- COMMAND`; that command's arguments are opaque. No session killing/deletion, closing panes/tabs, input injection, plugins, or remote-session authentication options. |
| `strace` | Reviewed long options before the program, or attachment with a positive numeric PID | Preserves short-option clusters, values, filters, output paths, and optional attached values. Stops at the first program argument or `--`. Requires a trace target. No syscall injection/faults, output-as-command, user switching, daemonization, or kill-on-exit. Valid long-option abbreviations are left alone. Flag corrections are local-only. |

Reviewed Zellij actions: `list-panes`, `list-tabs`, `list-clients`,
`current-tab-info`, `query-tab-names`, `dump-layout`, `focus-next-pane`,
`focus-previous-pane`, `focus-last-pane`, `move-focus`, `move-focus-or-tab`,
`go-to-next-tab`, `go-to-previous-tab`, `go-to-tab`, `go-to-tab-name`,
`rename-tab`, `rename-pane`, `rename-session`, `new-pane`, `new-tab`, `detach`,
`toggle-fullscreen`, `scroll-up`, `scroll-down`, `scroll-to-top`, and
`scroll-to-bottom`.

The exact reviewed option names and argument counts live in
[`data/nested-profiles.json`](../data/nested-profiles.json). An eligible spelling
must also be advertised by the installed executable's metadata. Nix's
`__dump-cli` supplies structured command and option arity information; missing
or incompatible metadata disables its suggestions. The other three adapters
use fixed `--help` queries. Metadata requests never include user operands,
credentials, or command payloads. Existing executable-identity checks,
one-hour help caching, timeouts, and cancellation apply.

A suggestion changes one syntax token, then passes the complete corrected
argument vector through the adapter again. Models can only select a reviewed
command candidate; they receive command syntax without operand or option
values. Invalid remaining syntax prevents the suggestion from being offered.
All accepted commands still require Enter.

## Examples

```text
nix biuld nixpkgs#hello               → nix build nixpkgs#hello
iwctl station wlan0 conenct 'My WiFi' → iwctl station wlan0 connect 'My WiFi'
zellij action list-paens --json      → zellij action list-panes --json
strace --follow-froks echo hello      → strace --follow-forks echo hello
```

Literal `#` inside an argument now works, including Nix flake references.
A `#` beginning an unquoted shell word remains unsupported comment syntax.

## Validation and provenance

The four executables were unavailable in the host PATH. Their Linux repository
packages and missing runtime libraries were extracted into a temporary
directory, without installing packages or starting services. Package SHA256s
were checked against the local pacman sync database. Captured versions:

- Nix 2.35.3-1
- iwd/iwctl 3.12-2
- Zellij 0.45.1-1
- strace 7.2-1

[Package provenance](../tests/fixtures/nested-cli-provenance.json) records the
package URLs and hashes. [Captured metadata](../tests/fixtures/nested-cli-help.json)
contains 36 fixed queries. No Wi-Fi changes, real sessions, builds, or traces
were executed during testing. Captured metadata tests grammar behavior; it does
not establish compatibility with every release or operating environment.

Checks completed:

- 10 Rust unit tests and 60 integration tests passed, including all
  1,823 catalog regression cases.
- 29 new positive corrections also passed against the extracted real binaries'
  metadata. Each corresponding correctly spelled command was left alone in
  fixture tests.
- Negative cases cover excluded operations, malformed arguments, opaque command
  payloads, private selectors, missing metadata, and changed Nix option arity.
- Mocked model tests verify operand/credential privacy and full revalidation.
- Real Bash PTY tests verify cancellation and Enter acceptance for all four
  roots, with exact arguments delivered only to harmless mock executables.
- Release build, formatting, Clippy with warnings denied, and Bash syntax checks
  passed.

Recapture metadata from installed Linux tools with:

```bash
python3 tests/collect_nested_help.py --output /tmp/nested-cli-help.json
```

Use `--bin-dir /path/to/extracted/usr/bin` for extracted packages; supply any
necessary runtime library path through `LD_LIBRARY_PATH`. Review the output and
update provenance before replacing fixtures. This collector executes only the
fixed metadata queries in the registry.

Run the focused tests after building the release binary:

```bash
python3 -m unittest discover -s tests -p test_cli_nested.py -v
```

## Local response times

Release build, extracted real binaries, local-only mode, one fresh-cache lookup
and 25 warm-cache samples per command on the development machine. These numbers
measure Nudge's suggestion engine; the final column includes process startup.
No model calls or proposed commands were executed. Results vary by machine.

| Input | Cold engine ms | Warm median ms | Warm p95 ms | Warm process wall median ms |
|---|---:|---:|---:|---:|
| `nix flake shwo .` | 34.050 | 3.363 | 4.478 | 4.539 |
| `iwctl station wlan0 shwo` | 3.485 | 0.934 | 0.988 | 2.045 |
| `zellij action list-paens --json` | 12.299 | 0.872 | 0.957 | 2.060 |
| `strace --follow-froks echo hello` | 3.052 | 0.767 | 0.825 | 1.967 |

The larger Nix metadata response costs more to collect and parse. Warm lookups
still complete in a few milliseconds. The remaining top-priority names are
`crontab`, `ssh-keygen`, and `lsof`; they remain planned.
