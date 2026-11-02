# Distribution options

Distribution channels and their separate publication steps. Nudge downloads are
hosted on GitHub Releases. AUR and marketplace listings require separate submissions.

## Recommended route

Use **GitHub Releases for downloads** and an **AUR package for Arch-based users**.
Keep the project Linux/Bash-focused; it does not require a particular desktop.
Omarchy users can discover an AUR package through **Install > AUR**, which the
[current manual documents](https://omarchy.org/manual/other-packages/).

### 1. GitHub Releases

Publish the static Linux x86_64 bundle, matching source archive, `SHA256SUMS`,
license notices, and release notes from one clean, tested commit at
[the repository's releases page](https://github.com/gammamike/nudge/releases).
Create a draft first, attach and verify all assets, then publish the release.
GitHub supports draft releases and attached binary assets; see its
[release instructions](https://docs.github.com/en/repositories/releasing-projects-on-github/managing-releases-in-a-repository).

The package workflow creates temporary CI artifacts. The tag workflow verifies
the tested assets and prepares a draft release for publication. Test installation
and removal from the actual published downloads. The
[packaging guide](PACKAGING.md) explains the existing build and verification steps.

### 2. AUR

There is a name collision: **`nudge` and `nudge-bin` already package an unrelated
Electron health application**. The official AUR RPC returned both names with
upstream `https://github.com/aasmart/Nudge` on the research date. Proposed names
`nudge-bash` and `nudge-bash-bin` returned no entries. That is a point-in-time
availability check, not a reservation. Recheck through the
[AUR package API](https://aur.archlinux.org/rpc/v5/info?arg%5B%5D=nudge&arg%5B%5D=nudge-bin&arg%5B%5D=nudge-bash&arg%5B%5D=nudge-bash-bin)
before submission.

Recommended package names:

- `nudge-bash`: build a tagged source release with Cargo.
- `nudge-bash-bin`: install the verified prebuilt Linux x86_64 release.

An AUR submission contains `PKGBUILD`, `.SRCINFO`, and any small packaging files;
the upstream downloads stay on GitHub. Create an AUR account, configure an SSH
public key, commit the packaging recipe to its AUR Git repository, and push its
`master` branch. Regenerate `.SRCINFO` with `makepkg --printsrcinfo` on each version
update. See the [AUR submission guidelines](https://wiki.archlinux.org/title/AUR_submission_guidelines)
and their [accessible translated edition](https://wiki.archlinux.org/title/AUR_submission_guidelines_%28Italiano%29).

For source builds, fetch locked dependencies in `prepare()` and build offline
with the lockfile in `build()`. Declare Cargo as a build dependency, Bash 5+ as a
runtime dependency, and optional model backends separately. Follow the
[Rust packaging guidance](https://wiki.archlinux.org/title/Rust_package_guidelines),
test in a clean Arch chroot, and inspect the package with `namcap` as described in
the [package guidelines](https://wiki.archlinux.org/title/Arch_package_guidelines).

**Packaging implementation:** the repository now provides the staged layout,
`nudge-bash` command, explicit Bash activation, lifecycle protection, and source
and binary recipe generation. See [system installation](SYSTEM_INSTALL.md) and
[release/AUR maintenance](RELEASING.md). AUR listings are not yet published.
Submission requires a tested clean release, validation against
its actual download URLs, a name-availability recheck, and maintainer submission.

## Omarchy's plugin marketplace

There **is** a marketplace at [plugins.omarchy.org](https://plugins.omarchy.org/).
However, its plugins extend the long-running Quickshell desktop process. The
contract requires a manifest and QML entry points for a widget, panel, overlay,
menu, service, or bar. `omarchy plugin add` clones and validates a repository; it
does not run an installer. See the [shell plugin manual](https://omarchy.org/manual/shell-plugins/).

Nudge's optional [settings companion](OMARCHY_COMPANION.md) implements that
contract, with theme integration, provider/model selection, connection testing,
and setup instructions. Installing the companion leaves CLI installation and
Bash activation to the user. The CLI works independently of the desktop.

For a genuine compatible companion, publish its repository with the required
manifest, README, and license, validate it locally, then submit the repository,
category, and tags through the [marketplace publishing form](https://plugins.omarchy.org/publish.html).
The [registry's submission process](https://github.com/omacom/omarchy-plugin-marketplace)
requires validation of the submitted commit and maintainer approval.

## Discovery after release

Share an installable release and a short terminal demonstration in Omarchy's
[Show and tell discussions](https://github.com/omacom/omarchy/discussions/categories/show-and-tell).
Describe Linux/Bash compatibility, cancellation behavior, scoped command
coverage, and optional Codex, Claude Code, and local LLM support. Link to the
release and issue template. A community announcement is separate from package
hosting or official distribution inclusion.

Marketplace approval is independent of GitHub release publication. Until a
listing is approved, users can install the companion directly from its repository.
