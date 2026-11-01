#!/usr/bin/env bash
# Build a source checkout or install the binary included in a Linux bundle.
set -euo pipefail
[[ ${OSTYPE:-} == linux* ]] || { printf 'Nudge supports Linux only.\n' >&2; exit 1; }
(( BASH_VERSINFO[0] >= 5 )) || { printf 'Nudge requires Bash 5 or newer.\n' >&2; exit 1; }
nudge_source=$(builtin cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && builtin pwd)
if [[ -x $nudge_source/bin/nudge ]]; then
    [[ $(uname -m) == x86_64 ]] || { printf 'This binary bundle requires Linux x86_64. Use a source build on other architectures.\n' >&2; exit 1; }
    exec "$nudge_source/bin/nudge" install "$@"
fi
command -v cargo >/dev/null || { printf 'A source install requires Rust 1.88+ and Cargo.\n' >&2; exit 1; }
cargo build --locked --release --manifest-path "$nudge_source/Cargo.toml" --target-dir "${CARGO_TARGET_DIR:-$nudge_source/target}"
exec "${CARGO_TARGET_DIR:-$nudge_source/target}/release/nudge-rust" install "$@"
