#!/usr/bin/env bash
# Produce local Linux artifacts and their matching source; this never publishes.
set -euo pipefail
export LC_ALL=C
nudge_root=$(builtin cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && builtin pwd)
nudge_output=$nudge_root/dist
nudge_binary=
nudge_allow_dirty=0
while (( $# )); do
    case $1 in
        --output) nudge_output=${2:?missing output directory}; shift 2 ;;
        --binary) nudge_binary=${2:?missing binary path}; shift 2 ;;
        --allow-dirty) nudge_allow_dirty=1; shift ;;
        --help|-h) printf 'Usage: scripts/package.sh [--output DIR] [--binary STATIC_ELF] [--allow-dirty]\n'; exit 0 ;;
        *) printf 'Unknown option: %s\n' "$1" >&2; exit 1 ;;
    esac
done
for tool in git tar gzip sha256sum readelf strip python3 cargo rustc; do command -v "$tool" >/dev/null; done
nudge_version=$(sed -n 's/^version = "\([^"]*\)"/\1/p' "$nudge_root/Cargo.toml")
[[ $nudge_version =~ ^[0-9]+\.[0-9]+\.[0-9]+([-+][a-zA-Z0-9.-]+)?$ ]] || exit 1
nudge_dirty=$(git -C "$nudge_root" status --porcelain)
if [[ -n $nudge_dirty && $nudge_allow_dirty != 1 ]]; then
    printf 'Release packaging requires a clean checkout; --allow-dirty is for local testing only.\n' >&2
    exit 1
fi
[[ -z $(git -C "$nudge_root" ls-files --others --exclude-standard) ]] || {
    printf 'Stage new source files before packaging so the source archive is complete.\n' >&2; exit 1;
}
if [[ -z $nudge_binary ]]; then
    command -v cargo >/dev/null
    if [[ -z ${CARGO_ENCODED_RUSTFLAGS:-} ]]; then
        read -r -a nudge_flags <<< "${RUSTFLAGS:-}"
        CARGO_ENCODED_RUSTFLAGS=
        for nudge_flag in "${nudge_flags[@]}"; do
            CARGO_ENCODED_RUSTFLAGS+="${CARGO_ENCODED_RUSTFLAGS:+$'\x1f'}$nudge_flag"
        done
    fi
    export CARGO_ENCODED_RUSTFLAGS="${CARGO_ENCODED_RUSTFLAGS:+$CARGO_ENCODED_RUSTFLAGS$'\x1f'}--remap-path-prefix=$nudge_root=/usr/src/nudge"$'\x1f'"--remap-path-prefix=${CARGO_HOME:-$HOME/.cargo}=/usr/src/cargo"
    cargo build --locked --release --manifest-path "$nudge_root/Cargo.toml" --target x86_64-unknown-linux-musl --target-dir "${CARGO_TARGET_DIR:-$nudge_root/target}"
    nudge_binary=${CARGO_TARGET_DIR:-$nudge_root/target}/x86_64-unknown-linux-musl/release/nudge-rust
fi
[[ -x $nudge_binary ]] || { printf 'Missing executable: %s\n' "$nudge_binary" >&2; exit 1; }
[[ $("$nudge_binary" --version) == "nudge $nudge_version" ]] || { printf 'Binary and source versions differ.\n' >&2; exit 1; }
readelf -h "$nudge_binary" | grep -q 'Advanced Micro Devices X86-64'
if readelf -l "$nudge_binary" | grep -q INTERP || readelf -d "$nudge_binary" 2>/dev/null | grep -q NEEDED; then
    printf 'Release binary must be statically linked (x86_64-unknown-linux-musl).\n' >&2; exit 1
fi
mkdir -p -- "$nudge_output"
nudge_output=$(builtin cd -- "$nudge_output" && builtin pwd)
nudge_stage=$(mktemp -d "$nudge_output/.package-XXXXXX")
trap 'rm -rf -- "$nudge_stage"' EXIT
nudge_name=nudge-$nudge_version-linux-x86_64
mkdir -p "$nudge_stage/$nudge_name/bin"
install -m755 "$nudge_binary" "$nudge_stage/$nudge_name/bin/nudge"
strip --strip-all "$nudge_stage/$nudge_name/bin/nudge"
install -m755 "$nudge_root/install.sh" "$nudge_stage/$nudge_name/install.sh"
cp "$nudge_root/LICENSE" "$nudge_root/CHANGELOG.md" "$nudge_stage/$nudge_name/"
cp "$nudge_root/Makefile" "$nudge_root/nudge.bash" "$nudge_stage/$nudge_name/"
mkdir -p "$nudge_stage/$nudge_name/packaging"
cp "$nudge_root/packaging/package-managed" "$nudge_stage/$nudge_name/packaging/"
cp -R "$nudge_root/man" "$nudge_root/completions" "$nudge_stage/$nudge_name/"
cat > "$nudge_stage/$nudge_name/README.md" <<'README'
# Nudge for Linux x86_64

Nudge is a Rust command-correction tool for interactive Bash 5+. This bundle
contains a static Linux binary. Rust and Python are not needed to run it.

## Build and enable

Cloud fallback through your existing Codex login is enabled by default when
local rules cannot choose an eligible correction. For local rules only, add
`export NUDGE_LOCAL_ONLY=1` to ~/.bashrc before starting a new shell, and run
the same export in the current shell. This disables all model requests.

Verify SHA256SUMS from the trusted download location before extracting. From
this extracted directory, run `./install.sh` as your normal user, then `exec bash`.
The installer adds one managed block to ~/.bashrc and keeps a backup.
An earlier manual source block must be removed first, or use --no-modify-shell.

Run `nudge --version` to inspect the installed version. Re-run the installer from
a new verified bundle to update; `nudge rollback` restores the previous payload.
Run `nudge uninstall` to remove the installation and its managed Bash block.
Settings, cache, unrelated shell settings, and backups are retained.

## Providers

Providers are Codex (OpenAI), Claude Code (Anthropic), and local LLMs through
Ollama or a compatible local HTTP server. Model requests happen automatically
before the Enter-to-run prompt; Enter confirms execution, not sending data.
Requests include command syntax and candidate routes with descriptions, not
scrollback, unrelated history, or command output. Argument-aware adapters omit
operands; catalog matchers send accepted literal command words without redaction.
Ensure your local server performs inference locally. See docs/PROVIDERS.md
for data handling and docs/INSTALLATION.md for setup.
Local LLM inference also requires curl and a separately running model server.

## Source and notices

The matching nudge-VERSION-source.tar.gz is distributed alongside this bundle.
Use that archive for development documentation, source links, and build scripts.
BUILD-INFO records the source commit and whether this is a development build.
See LICENSE, THIRD_PARTY_NOTICES.md, and licenses/ for license texts and notices.
README
cp -R "$nudge_root/docs" "$nudge_stage/$nudge_name/docs"
# Include files linked from the README and contributor documentation.
cp "$nudge_root/CONTRIBUTING.md" "$nudge_root/SECURITY.md" "$nudge_stage/$nudge_name/"
cargo metadata --locked --filter-platform x86_64-unknown-linux-musl --format-version 1 --manifest-path "$nudge_root/Cargo.toml" > "$nudge_stage/metadata.json"
python3 "$nudge_root/scripts/package-notices.py" --metadata "$nudge_stage/metadata.json" --sysroot "$(rustc --print sysroot)" --output "$nudge_stage/$nudge_name"
nudge_commit=$(git -C "$nudge_root" rev-parse HEAD)
nudge_epoch=${SOURCE_DATE_EPOCH:-$(git -C "$nudge_root" show -s --format=%ct HEAD)}
[[ $nudge_epoch =~ ^[0-9]+$ ]] || { printf 'SOURCE_DATE_EPOCH must be an integer.\n' >&2; exit 1; }
printf 'version=%s\ntarget=x86_64-unknown-linux-musl\ncommit=%s\ndirty=%s\n' "$nudge_version" "$nudge_commit" "$([[ -n $nudge_dirty ]] && printf true || printf false)" > "$nudge_stage/$nudge_name/BUILD-INFO"
printf 'rustc=%s\n' "$(rustc --version)" >> "$nudge_stage/$nudge_name/BUILD-INFO"
tar -C "$nudge_stage" --sort=name --mtime="@$nudge_epoch" --owner=0 --group=0 --numeric-owner -cf - "$nudge_name" | gzip -n > "$nudge_output/$nudge_name.tar.gz"
git -C "$nudge_root" ls-files -z > "$nudge_stage/source-files"
tar -C "$nudge_root" --null -T "$nudge_stage/source-files" --mtime="@$nudge_epoch" --owner=0 --group=0 --numeric-owner --transform="s,^,nudge-$nudge_version-source/," -cf - | gzip -n > "$nudge_output/nudge-$nudge_version-source.tar.gz"
(
    builtin cd -- "$nudge_output"
    sha256sum "$nudge_name.tar.gz" "nudge-$nudge_version-source.tar.gz" > SHA256SUMS
)
printf 'Local artifacts: %s\n' "$nudge_output"
