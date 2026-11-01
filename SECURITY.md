# Security reporting

Nudge proposes commands that run with the current user's privileges after
confirmation. A bug that bypasses confirmation, changes preserved arguments,
exposes credentials, or permits model-supplied code execution is security-relevant.

## Report a vulnerability

Use GitHub's **Report a vulnerability** option in the repository's Security tab
when private reporting is enabled:
[private report](https://github.com/gammamike/nudge/security/advisories/new).
If that option is unavailable, open an issue asking the maintainer to establish
a private reporting channel. Do not include exploit details, credentials, or
private command data in that public request.

A private report should include the affected commit, Linux and Bash versions,
a minimal reproduction using placeholder data, expected behavior, observed
behavior, and potential impact. Do not execute damaging commands to demonstrate
an issue. There is no guaranteed response time or supported release series yet.

## Current boundaries

- Models select from eligible candidates; their output is not evaluated as shell
  code. All accepted corrections require Enter.
- Argument-aware adapters omit operand and option values from model requests.
  Catalog-based matchers send literal command words. See
  [provider privacy boundaries](docs/PROVIDERS.md#data-sent-and-failure-handling).
- Codex and Claude Code use their own CLI authentication; local LLMs use loopback
  endpoints. Nudge does not manage provider tokens or install model weights.
- Installed executables and their metadata are trusted inputs. Reviewed grammar
  and confirmation reduce unintended corrections but do not prove a command is
  harmless. Inspect each suggestion before accepting it.
