# Development conventions

This repository is the working source for Nudge. Linux and Bash 5+ are the only
supported platforms. Keep command support claims scoped to tested behavior.

## Commits and documentation

- Use the maintainer's configured Git identity.
- Describe the actual change in commit messages. Do not append automated
  authorship credits, co-author trailers, or generated-by notices.
- Write README and release text for users: behavior, setup, limitations, and
  reproducible checks. Omit conversations and development-assistant attribution.
- Provider names belong in documentation where they explain supported features
  or configuration.
- Do not commit credentials, personal configuration, caches, build output, or
  private machine paths. Inspect staged files before committing; ignore rules
  do not protect secrets accidentally embedded in source or tracked files.

## Layout and validation

- Runtime: `src/`, `data/`, and `nudge.bash`.
- Integration tests in `tests/` exercise the Rust binary through mocks and PTYs;
  there is no second runtime implementation.
- Build with `cargo build --locked --release`.
- Run `cargo fmt --check`, `cargo clippy --locked --all-targets -- -D warnings`,
  `cargo test --locked`, and `python3 -m unittest discover -s tests -v`.
- Run `bash -n` separately for `nudge.bash`, `interactive.bash`, `try-bash`,
  `install.sh`, each `scripts/*.sh`, and `tests/distribution-smoke.sh`.
- Integration tests must use mocks for accepted commands and model requests.
  Never execute a proposed system/file/package operation just to test a correction.
- Keep the per-executable support matrix and fixtures consistent with changes.
