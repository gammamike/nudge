# Release and AUR maintenance

Nudge targets Linux and interactive Bash 5+. The currently tested binary target
is Linux x86_64 musl. Source and binary archives share one version and commit.
GPL-3.0-only remains the project license. No registry publication is implicit in
a local build, Makefile install, or recipe-generation command.

## Prepare a version

1. Finish the intended changes, update `CHANGELOG.md`, and write the user-facing
   release notes in `docs/releases/vX.Y.Z.md`.
2. Set the version in `Cargo.toml`, update `Cargo.lock`, and run the documented
   Rust, integration, package, and Arch checks.
3. Commit a clean tree and choose the matching `vX.Y.Z` tag. Push the commit and
   tag when ready to create a release draft.

The tag workflow reuses Linux checks and Linux packages. These include the
minimum Rust version, four distribution lifecycle checks, and clean Arch source
and binary package checks. Only after those pass does it verify archive hashes,
Cargo/archive/tag version agreement, clean build identity, and the tagged commit.
It creates a **draft** GitHub release with the static archive, matching source,
and `SHA256SUMS`. Review the draft and publish it explicitly. The workflow refuses
an existing release; never replace assets for an already published version.
Use a new version for changed release contents.

Archives retain the existing names:

- `nudge-X.Y.Z-linux-x86_64.tar.gz`
- `nudge-X.Y.Z-source.tar.gz`
- `SHA256SUMS`

The binary bundle includes its binary, per-user installer, staged-install
Makefile and Bash hook, man page, Bash completion, docs, and license notices.
Use [system installation](SYSTEM_INSTALL.md) for Makefile/package setup or
[per-user installation](INSTALLATION.md) for the managed home-directory layout.

## Prepare AUR packages

Names are `nudge-bash` (source) and `nudge-bash-bin` (prebuilt). Recheck availability
before first submission. The public executable is `nudge-bash`; neither package
claims to provide the unrelated application `nudge`. The binary variant provides
and conflicts with `nudge-bash`, so the two variants cannot be installed together.

After publishing and verifying the release downloads, run on Arch as a normal
user, with Python 3.11+ and `makepkg` available:

```bash
python3 scripts/prepare-aur.py --dist dist --output /tmp/nudge-aur-X.Y.Z
```

Use a new output directory each time. The helper verifies hashes and clean build
identity, fills the two recipes with the exact archive SHA-256 values, and uses
`makepkg --printsrcinfo` to generate `.SRCINFO`. It performs no downloads,
installation, submission, or credential access. `--allow-development` exists for
local tests and marks recipes as unsuitable for submission. Stable AUR recipes
currently require an `X.Y.Z` version; prerelease/versioned VCS packages need a
separate version policy. There are no checksum `SKIP` placeholders in generated
release recipes.

The source package fetches locked Cargo dependencies in `prepare()`, builds
with `--frozen`, tests Rust and staged installation in `check()`, then copies
prepared files under `$pkgdir/usr`. Python and Cargo are build-time tools only.
The binary package reuses the exact release executable and its license notices.
Neither package runs the per-user installer or edits a user's Bash startup files.
Codex, Claude Code, and local LLMs remain optional; local HTTP inference needs
`curl` and a separately configured server. Users explicitly enable the Bash hook.

## Validate and submit

`scripts/test-arch.sh dist` builds both variants in a disposable Arch container,
checks them with `namcap`, and exercises pacman installation/reinstallation,
a packaging-only upgrade, activation, lifecycle protection, removal, and
user-data preservation. Its base
image is pinned; package updates inside the image follow Arch's current mirrors.
It requires Docker and network access for toolchain/dependency preparation.
Host packages and shell configuration are not changed. Inspect any lint warnings;
errors fail the check. The regular integration suite covers Enter/cancel with mocks.

Local validation results are recorded in [the distribution report](DISTRIBUTION_TESTS.md#system-package-validation).

Before submission, test the recipes against the actual published URLs with a fresh
source cache as well. An AUR account with an SSH public key is needed to push.
Commit only the reviewed `PKGBUILD`, generated `.SRCINFO`, and any necessary small
packaging files to each package's separate AUR Git repository on `master`.
Do not upload binary packages, credentials, build output, or our whole source repo.
For a new upstream version, update `pkgver`, reset `pkgrel` to 1, regenerate hashes
and `.SRCINFO`, and retest. Bump `pkgrel` for packaging-only revisions.

No AUR account, SSH secret, automatic AUR push, or crates.io publishing credential
is needed by the repository workflows. AUR submission remains a maintainer action.
See the [AUR rules](https://wiki.archlinux.org/title/AUR_submission_guidelines),
[Rust packaging guidance](https://wiki.archlinux.org/title/Rust_package_guidelines),
and [package guidelines](https://wiki.archlinux.org/title/Arch_package_guidelines).

## Additional channels

ARM binaries, crates.io, DEB/RPM, Nix packaging, and a VCS AUR variant remain
future distribution work. Add them with architecture-specific validation and
correct shell-hook installation instructions. `cargo install` alone does not
install the Bash hook, notices, man page, or completions; `publish = false`
therefore remains intentional. Nudge does not advertise other shell integrations.
