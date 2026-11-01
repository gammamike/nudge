# Development

Nudge targets Linux and Bash 5+. Runtime code is in `src/`; reviewed Linux
profiles are in `data/linux-profiles.json`. `nudge.bash` integrates the release
binary with the interactive shell.

## Checks

```bash
cargo build --locked --release
cargo fmt --check
cargo clippy --locked --all-targets -- -D warnings
cargo test --locked
python3 -m unittest discover -s tests -v
bash -n nudge.bash interactive.bash try-bash
```

Use `--offline` with Cargo after the locked dependencies have been downloaded.
Integration tests need Python 3, `curl`, pseudo-terminals, and permission to bind
loopback test servers. They use temporary state and mock providers; they do not
need subscription credentials or execute proposed real-world operations.

`tests/reference/python/` contains the earlier correction engine and terminal
contract for parity checks. Its source is included here so tests do not depend
on a sibling checkout. Captured Herdr/Omarchy help supplies the legacy catalog.

## Fixtures and coverage

- `legacy-help.json`: read-only Herdr/Omarchy metadata for cross-language parity.
- `linux-cli-help.json`: Git/Docker/systemd metadata for the first adapter batch.
- `linux-profile-help.json`: installed-help snapshots for the additional profiles.
- `linux-profile-cases.json`: one positive regression case per profile.
- `linux-profile-versions.json`: version provenance for those snapshots.

All fixture paths above are relative to `tests/fixtures/`. Use placeholders for
personal paths and identifiers. Do not capture account configuration or command
history. Public help output in fixtures remains attributable to the upstream
programs; the project license does not replace upstream notices.

Adding a tool requires explicit syntax and argument rules, read-only discovery,
positive and refusal tests, and an updated support matrix. A name in the roadmap
is not implemented support. Tests of accepted corrections must use mock
executables or explicitly disposable resources.

## Benchmarks

Metadata-only suggestions against installed tools:

```bash
python3 tests/benchmark_profiles.py --samples 25 --output /tmp/nudge-profile-benchmark.json
```

This checks all recorded profile examples and requires those tools to be
installed. It does not execute the proposed corrections.

Optional comparisons with the Python reference:

```bash
python3 benchmarks/compare.py
python3 benchmarks/compare_terminal.py
```

The comparison scripts require installed Herdr/Omarchy. The terminal script
cancels every correction. `compare.py --codex` makes real provider requests and
consumes account usage; ordinary tests do not. Locally produced comparison
results are ignored by Git. Historical profile timing records are kept as
fixtures and describe the tested machine and scope, not a performance guarantee.

## Repository hygiene

The `.gitignore` excludes environment files, provider/credential directories,
private keys, local configuration, caches, build output, logs, and temporary
files. Keep `Cargo.lock` and reviewed fixtures tracked. Example configuration
must contain placeholders only.

Before committing, inspect `git diff --cached` and the staged filenames. Ignore
rules do not remove already tracked files or detect credentials embedded in
source. If an actual credential is committed, revoke or rotate it and assess the
repository history; adding its filename to `.gitignore` is not remediation.
