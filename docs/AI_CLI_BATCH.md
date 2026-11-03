# AI CLI command corrections

This batch adds four executable adapters, bringing the registry to **271**.
It corrects command syntax locally; it does not add Gemini as a fallback provider
or change the existing Codex, Claude Code, and local LLM provider integrations.

## Supported scope

| Executable | Reviewed forms | Example correction |
|---|---|---|
| `codex` | Help/version; `login status`; `mcp list`, `mcp get NAME`, including `--json` | `codex login statua` → `codex login status` |
| `claude` | Help/version; `auth status` with `--json` or `--text`; `mcp list`, `mcp get NAME` | `claude auth statua --text` → `claude auth status --text` |
| `ollama` | Help/version; `list`/`ls`, `ps`; `show MODEL` with `--license`, `--modelfile`, `--parameters`, `--system`, `--template`, `--verbose` | `ollama show qwen3:0.6b --paramters` → `ollama show qwen3:0.6b --parameters` |
| `gemini` | Help/version; `--list-sessions`, `--list-extensions`; `mcp list`; `extensions list` with `--output-format` | `gemini mcp lsit` → `gemini mcp list` |

Short flags retain their declared arity but are not guessed. Server names, model
names, and option values remain literal. Installed help must advertise a target;
a captured fixture alone never grants runtime support. Corrections still require
Enter to run, and any other key cancels.

## Boundaries

These adapters are local-only, including when `--force-ai` is requested. No
command words, prompts, model names, or server names are sent to a fallback
provider. Metadata queries use only the registry's fixed help routes.

Codex, Claude Code, and Gemini accept free-form prompts at the root, so their
root command words are never rewritten. Type a reviewed namespace such as
`codex login`, `claude auth`, or `gemini mcp` correctly; corrections then apply
inside that namespace. Root informational flag typos such as `--verison` can
also be corrected. Prompt text and inference options are excluded.

Model execution/download/upload/removal, agent execution, interactive sessions,
login/logout, permission bypass, installing/updating extensions or tools, and
MCP configuration changes are outside this first batch. Existing advertised
commands and aliases are preserved. A valid reviewed command that fails because
of authentication, connectivity, or a missing model is not rewritten. MCP
inspection can contact configured servers when the user accepts execution.

## Validation

Captured Linux versions: Codex CLI 0.166.0, Claude Code 2.1.316, Ollama package
0.40.7-1, and Gemini CLI 0.64.0. See
[`ai-cli-provenance.json`](../tests/fixtures/ai-cli-provenance.json) for package
checksums and capture boundaries. Help lives in the nested CLI fixtures.

Each tool has positive correction cases, valid-command failures, missing-help
checks, and Bash PTY acceptance/cancellation coverage. Tests also check unchanged
quoted arguments, opaque prompts, excluded operations, future advertised
commands, and no provider requests, including forced-model mode. Accepted
commands run only harmless doubles, never the real AI CLIs.
