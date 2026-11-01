# Changelog

User-visible changes are recorded here. Unreleased entries are available in the
source tree and do not imply a published package or stable release.

## Unreleased

### Added

- Rust correction engine and interactive Bash 5+ integration for Linux.
- Enter-to-run confirmation, single-key cancellation, and literal argument passing.
- 120 scoped executable adapters, with installed command metadata and explicit
  eligibility rules. See the [coverage documentation](README.md#command-coverage).
- Nix, iwctl, Zellij, and strace adapters with nested-command, selector, option,
  and command-payload handling.
- Optional Codex and Claude Code subscription CLI selection, plus local LLMs
  through Ollama and compatible local HTTP servers; configurable models.
- Local-only mode, metadata caching, request timeouts, and cancellation cleanup.
- Linux CI, contribution and issue templates, troubleshooting, and security
  reporting guidance.

### Changed

- Literal `#` inside an argument is accepted for forms such as Nix flake references.
- Catalog and shell regressions validate the Rust executable against fixed
  expected results and mocks.

### Release status

Source-checkout installation is available. A standalone installer, distribution
packages, release artifacts, and broader clean-distribution validation remain
planned. Hosted CI results must be reviewed after the workflow is first pushed.
