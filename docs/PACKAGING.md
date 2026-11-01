# Linux packaging and validation

The packaging script produces local artifacts. It does not push Git commits,
create tags, upload releases, or install software on the development host.

## Build artifacts

Use a clean Git checkout, Rust/Cargo, the `x86_64-unknown-linux-musl` target,
Python 3 for notice collection, and GNU tar, gzip, sha256sum, readelf, and standard
file utilities. Fetch locked Cargo dependencies before working offline.

```bash
rustup target add x86_64-unknown-linux-musl
scripts/package.sh
```

Output in `dist/`:

- `nudge-VERSION-linux-x86_64.tar.gz`: static binary, installation wrapper,
  user documentation, build identity, and dependency/toolchain license notices.
- `nudge-VERSION-source.tar.gz`: corresponding tracked source and build files.
- `SHA256SUMS`: SHA-256 checksums of both archives.

The binary is checked for the expected version, architecture, and absence of a
runtime ELF interpreter or shared-library requirements. Build paths are remapped
to neutral source prefixes. The installer retains bundled license notices when
copying the payload into its per-user location.

`BUILD-INFO` records the version, target, source commit, toolchain, and dirty-tree
status. Archive timestamps use the commit time, or `SOURCE_DATE_EPOCH`. Sorted
entries, fixed ownership, and gzip without timestamps make repeated archive
creation reproducible for identical inputs. This does not claim bit-for-bit
reproducible compilation across different toolchains or environments.

For local testing, `--allow-dirty` packages tracked working-tree contents; stage
new files first. Never publish a dirty artifact as a stable release. `--binary`
can reuse an already-built static executable; select the same Rust toolchain
that built it so the collected toolchain notices match. `--output` changes the
artifact directory.

## Distribution checks

The [Linux packages workflow](../.github/workflows/packages.yml) builds one
bundle and tests it in pinned Ubuntu, Debian, Fedora, and Alpine images. It runs
on pushes to main, pull requests, and manual dispatch. The workflow retains
artifacts for 14 days and does not publish a release.

To run one image locally with Docker:

```bash
scripts/test-distribution.sh dist/nudge-0.1.0-linux-x86_64.tar.gz ubuntu:24.04
```

Use the digests recorded in [the validation report](DISTRIBUTION_TESTS.md) for
an exact base image. The test runner verifies checksums, prepares Bash on Alpine,
then runs the smoke test as UID 1000 with network access and capabilities disabled.
Only the disposable image/container and temporary test state are changed. It
checks installation, repeated installation, update, rollback, Bash hook loading,
local correction with a mock executable, and uninstall/data preservation.

The local validation report distinguishes isolated userspace checks from a
hosted workflow run. Containers share a host kernel; they do not establish full
VM, desktop-session, architecture, or all-command compatibility. CLI adapters
still require their own versioned metadata and tests.

## Before publishing a release

1. Confirm Rust tests, integration tests, and the distribution workflow pass for
   the exact commit. Inspect the source and binary archives and staged files.
2. Set the intended package version and changelog entry; build from a clean tree.
3. Publish both archives, their checksums, and accurate architecture/compatibility
   notes together. Preserve the source and license notices with the binary.
4. Verify install and removal from the published downloads and record the result.
5. Enable private vulnerability reporting in repository settings.

AUR, DEB/RPM packages, package repositories, ARM binaries, and automatic network
updates are not provided by this installer. Users update explicitly from source
or a verified bundle.
