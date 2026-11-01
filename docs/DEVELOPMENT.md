# Development

Nudge targets Linux and Bash 5+. Runtime code is in `src/`; reviewed Linux
profiles are in `data/linux-profiles.json` and `data/nested-profiles.json`. `nudge.bash` integrates the release
binary with the interactive shell.

## Checks

```bash
cargo build --locked --release
cargo fmt --check
cargo clippy --locked --all-targets -- -D warnings
cargo test --locked
python3 -m unittest discover -s tests -v
for script in nudge.bash interactive.bash try-bash install.sh scripts/*.sh tests/distribution-smoke.sh; do bash -n "$script"; done
```

Use `--offline` with Cargo after the locked dependencies have been downloaded.
Integration tests need Python 3, `curl`, pseudo-terminals, and permission to bind
loopback test servers. They use temporary state and mock providers; they do not
need subscription credentials or execute proposed real-world operations.

The integration harness in `tests/` invokes the compiled Rust binary. Shared
PTY helpers live in `tests/support.py`; expected catalog behavior is stored as
fixed regression fixtures. Codex, Claude Code, and local LLM providers all use
mocks during automated checks.

[Linux CI](../.github/workflows/ci.yml) runs the checks above on stable Rust and
the minimum supported Rust version (1.88). It uses read-only repository
permissions and requires no provider credentials. Its first hosted result must
be checked after the workflow is pushed.

## Installer and distribution checks

The installer is part of the Rust executable (`src/install.rs`); `install.sh`
wraps source builds and binary bundles. `src/paths.rs` supplies relocatable XDG
paths. Installer integration tests use disposable homes and mock commands to
cover installation, updates, rollback, conflicts, backups, and Bash behavior.
No test should install into the developer's real home directory.

`scripts/package.sh` creates a static Linux bundle, matching source, checksums,
and notices. Python is used only for developer tests and notice collection.
See [packaging](PACKAGING.md) and [distribution results](DISTRIBUTION_TESTS.md).
The separate package workflow validates Ubuntu, Debian, Fedora, and Alpine.

## Fixtures and coverage

- `catalog-help.json`: captured help for catalog-based command discovery.
- `catalog-entries.json`: expected discovery entries.
- `catalog-cases.json`: 1,823 fixed correction and refusal cases.
- `linux-cli-help.json`: Git/Docker/systemd metadata for the first adapter batch.
- `linux-profile-help.json`: installed-help snapshots for the additional profiles.
- `linux-profile-cases.json`: one positive regression case per profile.
- `linux-profile-versions.json`: version provenance for those snapshots.
- `nested-cli-help.json`: fixed Nix, iwctl, Zellij, and strace metadata queries.
- `nested-cli-provenance.json`: package versions, URLs, and hashes for that capture.

All fixture paths above are relative to `tests/fixtures/`. Use placeholders for
personal paths and identifiers. Do not capture account configuration or command
history. Public help output in fixtures remains attributable to the upstream
programs; the project license does not replace upstream notices.

Adding a tool requires explicit syntax and argument rules, read-only discovery,
positive and refusal tests, and an updated support matrix. A name in the roadmap
is not implemented support. Tests of accepted corrections must use mock
executables. Do not run a proposed system/file/package operation as a test.

## Benchmarks

Metadata-only suggestions against installed tools:

```bash
python3 tests/benchmark_profiles.py --samples 25 --output /tmp/nudge-profile-benchmark.json
```

This checks all recorded profile examples and requires those tools to be
installed. It does not execute the proposed corrections.

Historical timing records describe the tested machine and scope, not a
performance guarantee. Record the tool versions, sample count, cache state, and
whether timings include process startup. Measure model latency separately from
local matching. Ordinary tests never make live provider requests.

## Comments and documentation

- Describe current behavior, supported forms, and limitations. Keep development
  history in Git and user-visible changes in the changelog.
- Use module docs for purpose and boundaries. Use inline comments for intent,
  non-obvious invariants, or reasons for conservative behavior; avoid narrating
  straightforward code. Format Rust with `cargo fmt`.
- Describe Nudge as a Linux/Bash tool. Distribution names belong only in exact
  adapter names, fixture provenance, or a stated compatibility result.
- General provider descriptions must include Codex, Claude Code, and local LLMs.
  Provider-specific code, settings, and authentication instructions should name
  the provider they actually apply to. Distinguish deterministic local matching
  from local model inference.
- Keep examples copyable and use placeholders for user-specific values. Label
  alternative configurations so readers do not run every example in sequence.
- Use relative links within the repository. Keep implemented coverage separate
  from planned tools and historical validation results.

## Repository hygiene

The `.gitignore` excludes environment files, provider/credential directories,
private keys, local configuration, caches, build output, logs, and temporary
files. Keep `Cargo.lock` and reviewed fixtures tracked. Example configuration
must contain placeholders only.

Before committing, inspect `git diff --cached` and the staged filenames. Ignore
rules do not remove already tracked files or detect credentials embedded in
source. If an actual credential is committed, revoke or rotate it and assess the
repository history; adding its filename to `.gitignore` is not remediation.
