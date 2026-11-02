# Changelog

User-visible changes are recorded here. Unreleased entries are available in the
source tree and do not imply a published package or stable release.

## Unreleased

### Added

- Explicit provider/model connection tests in the settings panel and CLI,
  using synthetic data without changing saved choices.
- Optional Omarchy settings panel with live theme integration, Codex, Claude
  Code, and local LLM provider/model selection, local model discovery, and
  installation and Bash activation instructions.
- Staged Makefile installation, a `nudge-bash` entry point, man page, Bash
  completion, and package-managed lifecycle protection.
- Checksum-pinned AUR recipe generation, isolated Arch package checks, and
  a version/commit-verified draft-release workflow.

- Rust correction engine and interactive Bash 5+ integration for Linux.
- Enter-to-run confirmation, single-key cancellation, and literal argument passing.
- 267 scoped executable adapters, with installed command metadata and explicit
  eligibility rules. See the [coverage documentation](README.md#command-coverage).
- Nix, iwctl, Zellij, and strace adapters with nested-command, selector, option,
  and command-payload handling.
- Optional Codex and Claude Code subscription CLI selection, plus local LLMs
  through Ollama and compatible local HTTP servers; configurable models.
- Local-only mode, metadata caching, request timeouts, and cancellation cleanup.
- Linux CI, contribution and issue templates, troubleshooting, and security
  reporting guidance.

- Per-user Rust installer with managed Bash setup, backups, explicit updates,
  rollback, and uninstall that preserves user settings and cache.
- Static x86_64 Linux bundle, matching source archive, checksums, and dependency
  notices; package CI matrix for Ubuntu, Debian, Fedora, and Alpine.

- 147 additional executable adapters across 12 tested batches, plus Docker Buildx
  inspection commands, with captured metadata and regression cases.

### Changed

- Keep connection-test results when saving or reloading unchanged choices or
  switching settings tabs; clear them when connection choices change.
- Fallback messages distinguish no suitable correction from invalid model
  responses, alongside separate authentication and timeout errors.
- Local-only adapter policies also apply when `--force-ai` is requested.
- Nested aliases and Kubectl global options are validated against installed help.
- Required inspection/dry-run flags cannot be satisfied by argument values.
- Configuration and cache follow XDG paths; installed copies no longer depend
  on the source checkout.
- Literal `#` inside an argument is accepted for forms such as Nix flake references.
- Catalog and shell regressions validate the Rust executable against fixed
  expected results and mocks.

### Release status

Source and binary-bundle installation are implemented. Local lifecycle tests
passed in isolated Ubuntu, Debian, Fedora, and Alpine userspaces. Public release
artifacts, native distribution packages, other architectures, and broader CLI
coverage remain pending. The previous main commit passed both hosted workflows; the new command
expansion still needs hosted CI after it is pushed.
