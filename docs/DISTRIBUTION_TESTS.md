# Linux distribution validation

Local validation on 2026-11-01 used the same static x86_64 musl bundle in four
isolated Linux userspaces. All four passed the installer lifecycle smoke test.

| Image | Reported distribution | Bash | Result |
|---|---|---|---|
| `ubuntu:24.04` | Ubuntu 24.04.5 LTS | 5.2.21 | Passed |
| `debian:12-slim` | Debian GNU/Linux 12 (bookworm) | 5.2.15 | Passed |
| `fedora:43` | Fedora Linux 43 Container Image | 5.3.0 | Passed |
| `alpine:3.22` | Alpine Linux v3.22 | 5.2.37 | Passed after installing Bash and coreutils |

[Machine-readable results and image digests](../tests/fixtures/distribution-results.json)
identify the exact base images. OCI manifests and layers were verified against
their SHA-256 digests before extraction. Docker was inaccessible on the local
host, so Bubblewrap user namespaces supplied isolated filesystems instead. Files
were extracted with owner access for rootless testing. No host packages, services,
or shell configuration were changed. Smoke tests ran without network access;
Alpine package preparation used its own disposable filesystem beforehand.

The checks covered first install, repeated install without duplicate setup,
update with a distinct executable payload, rollback, loading the installed Bash
hook, a local correction using a harmless mock, and uninstall while retaining
settings and cache. Host integration tests separately verify real PTY Enter/cancel
behavior, quoted paths, conflicts, backups, and preservation of shell content.

These are userspace tests on a shared kernel, not full VM or desktop tests. They
do not certify every CLI adapter on each distribution or any other architecture.
The pinned Docker CI matrix runs the same smoke script as an unprivileged user;
the previous main commit passed both [Linux checks](https://github.com/gammamike/nudge/actions/runs/41342149216)
and [Linux packages](https://github.com/gammamike/nudge/actions/runs/41342149273).
Hosted validation of the current command expansion remains pending until push.

See [packaging instructions](PACKAGING.md) to reproduce the checks and
[installation instructions](INSTALLATION.md) for supported setup options.

## Command expansion recheck

The 260-adapter expansion was rebuilt with Rust 1.88.0 for
`x86_64-unknown-linux-musl`. Its development bundle passed the same lifecycle
smoke test in all four userspaces above, with read-only bundle mounts and
networking disabled. [Results and tested archive hash](../tests/fixtures/expansion-distribution-results.json)
record that local run. This does not substitute for hosted CI and published-download
checks on a final release.
