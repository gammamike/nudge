# CLI support request

Suggested issue title: `CLI support: <executable>`

Search for an existing request first. Copy this template into the Nudge issue
tracker once it is published. Replace private values with consistent placeholders;
do not attach credentials, complete shell history, or account configuration.

## Tool

- Executable name(s):
- Official documentation/source URL:
- Tool version and implementation (for example, GNU vs. BusyBox):
- Distribution/version:
- Install method/package name:
- Is this an executable, Bash builtin, alias, function, or wrapper?

## What you expected

Describe the workflow this tool supports and which commands you use most.

| Mistyped command | Expected correction | Why this preserves your intent |
|---|---|---|
| | | |
| | | |

Do not run a destructive command just to reproduce a request. Clearly label
examples you have not executed.

## What Nudge must leave alone

Provide valid commands that can fail without needing a spelling/syntax fix,
ambiguous inputs, and argument values that must be preserved exactly. Include
quoted paths, resource names, or flags with values if relevant to your workflow.

## Command definitions

Attach or paste the relevant help output or link to the command reference.
State the read-only command used to obtain that output. Include the exit status
and a short redacted error message from your example if already available.

## Effects and constraints

- Does this command modify/delete data or affect a running service?
- Does it require elevated privileges?
- Does it communicate with a remote host or cloud account?
- Are there variants or plugins that change its syntax?

## Optional contribution

Can you help test an adapter on your installed version? Code contributions are
welcome, but they are not required to request a tool.
