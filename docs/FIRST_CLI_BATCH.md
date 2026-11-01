# Implemented first CLI batch — Linux/Bash

Git, Docker/Compose, systemctl, and journalctl now have initial argument-aware
adapters. This is scoped support, not a claim that every subcommand, flag, version,
or shell construct is supported. Herdr/Omarchy retain their original adapters.

## What works

| Tool | Examples of supported corrections |
|---|---|
| Git | `git statsu` → `git status`; `git chekout feature/topic` → `git checkout feature/topic`; `git status --shrot` → `git status --short`; `git logs --oneline -5` → `git log --oneline -5` |
| Docker | `docker contianer ls` → `docker container ls`; `docker logs --tial 10 api` → `docker logs --tail 10 api` |
| Docker Compose | `docker comopse ps` → `docker compose ps`; `docker compose -f 'compose dev.yml' restat api` → `docker compose -f 'compose dev.yml' restart api` |
| systemctl | `systemctl --user restat example.service` → `systemctl --user restart example.service`; `systemctl list-timres` → `systemctl list-timers` |
| journalctl | `journalctl --uint=example.service` → `journalctl --unit=example.service`; `journalctl --sinec '1 hour ago'` → `journalctl --since '1 hour ago'` |

Each suggestion changes one syntax token. Literal arguments are preserved,
including quoted spaces, empty strings, escaped characters, `--` boundaries,
and option values such as `--tail=10`. Display quoting may be normalized; the
executed argument values are unchanged. No suggestion executes before Enter.

Only correctly typed executable names are considered. Expansion, unquoted globs,
pipelines, redirects, compound commands, `sudo` wrappers, Bash functions, and
shell aliases remain unsupported. Quoted literal dollar signs are allowed, but
variable/command substitutions are not expanded or evaluated.

## Eligible command routes

The installed tool must also advertise a route before it becomes a candidate.
Unavailable routes are not offered. Known routes outside this table are left
alone, including close misspellings of excluded commands.

| Root / group | Eligible command names |
|---|---|
| `git` | `status`, `log`, `diff`, `show`, `blame`, `grep`, `describe`, `shortlog`, `ls-files`, `ls-tree`, `ls-remote`, `rev-parse`, `add`, `commit`, `fetch`, `pull`, `push`, `clone`, `init`, `branch`, `checkout`, `switch`, `merge`, `rebase`, `tag`, `help`, `version` |
| `docker` | `compose`, `container`, `image`, `network`, `volume`, `system`, `ps`, `images`, `logs`, `inspect`, `info`, `version`, `start`, `stop`, `restart`, `stats`, `top`, `port`, `history`, `events`, `run`, `exec`, `build`, `pull`, `push`, `tag`, `pause`, `unpause`, `wait` |
| `docker compose` | `ps`, `ls`, `logs`, `config`, `images`, `version`, `top`, `port`, `stats`, `start`, `stop`, `restart`, `pause`, `unpause`, `build`, `pull`, `push`, `up`, `run`, `exec`, `events`, `wait` |
| `docker container` | `ls`, `logs`, `inspect`, `start`, `stop`, `restart`, `stats`, `top`, `port`, `diff`, `run`, `exec`, `pause`, `unpause`, `wait` |
| `docker image` | `ls`, `inspect`, `history`, `pull`, `push`, `tag`, `build` |
| `docker network`, `docker volume` | `ls`, `inspect` |
| `docker system` | `df`, `info`, `events` |
| `systemctl` | `status`, `show`, `cat`, `help`, `is-active`, `is-failed`, `is-enabled`, `is-system-running`, `list-units`, `list-unit-files`, `list-timers`, `list-sockets`, `list-paths`, `list-automounts`, `list-dependencies`, `list-jobs`, `list-machines`, `show-environment`, `get-default`, `start`, `stop`, `restart`, `reload`, `try-restart`, `reload-or-restart`, `try-reload-or-restart`, `daemon-reload`, `enable`, `disable` |
| `journalctl` | Long-option correction, rather than subcommand correction. Query options come from installed help. Maintenance/key-generation/vacuum operations are excluded. |

Long-option typos are corrected only when there is a unique one-edit match.
Unknown short flags are declined. Existing short-flag clusters and attached
values are parsed to locate arguments; no short flag is guessed. Valid unique
long-option abbreviations for Git/systemd are left alone. Git's terse help omits
some shared options, so reviewed common Git 2.x log/show/diff options supplement
discovery. Unlisted/unrecognized forms are declined.

Git global support is limited to `-C`, `--git-dir`, `--work-tree`, `--no-pager`,
`--paginate`, and `--literal-pathspecs`. Git aliases/external subcommands are
checked fresh in the selected repository context and are not corrected. Git
configuration overrides such as `-c` are outside scope.

Docker context/host flags and Compose project/file options retain their values.
Docker `--config` is outside scope because it can change plugin resolution.
For Docker/Compose `run` and `exec`, arguments after the image/container/service
operand are treated as application payload and never corrected as Docker flags.
Standalone `docker-compose` and `docker buildx` are not implemented in this batch.

## Eligibility and failure handling

An input with recognized command and option syntax gets no speculative retry:
missing resources, permission/authentication failures, unavailable daemons, and
invalid option values are not diagnosed. Resource names are never looked up or
rewritten. Required option values and selected mandatory operand counts are
checked, but this is not a complete semantic validator for the underlying CLI.

Commands such as Git reset/clean/rm, Docker prune/rm/rmi/Compose down, and system
reboot/poweroff are not candidates. Force/delete/hard/discard/overwrite/prune
flags and selected tool-specific risky flags cause refusal, including recognized
abbreviations and short clusters. Git checkout path-restoration with `--` is
excluded. This is a conservative scope boundary, not a general command sandbox:
eligible actions such as commit, push, start, stop, restart, and Compose up can
still change data or services when the user presses Enter.

The adapters handle one correction at a time. If fixing a command word would
leave another unknown flag/command, no partial suggestion is offered.

Local matching is attempted first. If an unknown eligible command word cannot
be resolved locally, the configured AI provider may select a catalog command.
Only command syntax is sent in that request; preserved arguments, flag values,
paths, and resource operands are omitted. The chosen command is revalidated
against the original arguments before confirmation. Long-option corrections
remain deterministic; no AI request is made to guess an option.

## Metadata and verification

Discovery uses Git command listings and read-only `-h`/`--help` requests. It does
not probe running containers, restart services, run user workloads, or read logs.
Help is requested in the C locale, with pagers/colors disabled, and cached for
one hour against executable path/mtime/size and query. Compose's independent
plugin version is also checked. Git aliases are deliberately not cached.

Verified on Linux on November 1, 2026:

- Git **2.56.0**; Docker **29.9.2**; Compose **5.6.1**; systemd **262.1**.
- **42 integration tests** and **6 Rust unit tests** passed, including the prior
  provider tests and 1,823 legacy local-parity inputs.
- **26 suggestion-only checks** against actual installed metadata passed.
- **Five fresh normal-Bash checks** displayed and cancelled real suggestions.
  No suggested real command was executed. Accept/execute behavior was tested
  against fixtures, with exact argv comparison and one execution per Enter.
- Formatting, Clippy, release build, and Bash syntax checks passed.

The five single terminal observations were Git 16.62 ms, Docker 19.85 ms, Compose
130.75 ms, systemctl 9.28 ms, and journalctl 8.93 ms. These are smoke-test timings,
not a controlled benchmark; Compose performs additional plugin-version probes.

See [recorded installed checks](../tests/fixtures/installed-cli-smoke-results.json)
and [help fixtures](../tests/fixtures/linux-cli-help.json). Other tool versions
need additional verification before claiming compatibility. Live provider
accuracy for these new command families has not been benchmarked; provider
selection/argument privacy was tested with a simulated response.

New normal Bash shells load the updated hook automatically. Existing shells
need `exec bash` (or opening a new terminal) because their loaded hook still has
the previous executable list.

References: [Git CLI](https://git-scm.com/docs/git),
[Docker CLI](https://docs.docker.com/reference/cli/docker/),
[Compose CLI](https://docs.docker.com/reference/cli/docker/compose/),
[systemctl](https://www.freedesktop.org/software/systemd/man/latest/systemctl.html),
[journalctl](https://www.freedesktop.org/software/systemd/man/latest/journalctl.html).
