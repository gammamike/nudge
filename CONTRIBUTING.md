# Contributing to Nudge

Nudge is a Rust command-correction tool for interactive Bash 5+ on Linux.
Contributions to supported command forms, tests, documentation, and packaging
are welcome. Check existing issues before opening a new request or starting a
large change.

## Report a problem

Use the [bug report form](https://github.com/gammamike/nudge/issues/new?template=bug-report.yml)
for incorrect behavior, or the
[CLI support form](https://github.com/gammamike/nudge/issues/new?template=cli-support.yml)
for another tool or command form. Include your Linux distribution, Bash version,
Nudge commit, tool version, and a minimal example. Replace private values with
placeholders. Do not attach credentials, full history, or account configuration.
See [security reporting](SECURITY.md) for a possible vulnerability.

## Prepare a change

1. Build the release binary and follow the checks in
   [development notes](docs/DEVELOPMENT.md).
2. Keep the change focused. Explain the observable problem and resulting behavior.
3. For an adapter, declare its grammar, collect read-only metadata, and test
   corrections, refusals, literal arguments, and applicable command boundaries.
   Use harmless mocks when testing Enter-to-run behavior.
4. Update the relevant support matrix and the Unreleased changelog. A registered
   executable does not imply support for all its commands or options.
5. Review staged files for credentials, personal paths, generated output, and
   unrelated changes before committing.

The integration harness uses Python 3 to exercise the compiled Rust executable;
it does not provide a second implementation of Nudge. Codex, Claude Code, and
local LLM interactions are mocked. Contributors do not need provider accounts.

## Pull requests

Describe what changed, why, and which checks passed. Include important limits
and link a relevant issue when available. Commit messages should describe the
change in plain language. Follow the comment and documentation conventions in
[development notes](docs/DEVELOPMENT.md). Contributions are made under the
repository's [GPL-3.0-only license](LICENSE).
