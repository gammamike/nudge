#!/usr/bin/env bash
# Collect notices from the selected toolchain and already-fetched dependencies.
set -euo pipefail
nudge_output=${1:?usage: scripts/source-notices.sh OUTPUT}
mkdir -p -- "$(dirname -- "$nudge_output")"
nudge_stage=$(mktemp -d "$(dirname -- "$nudge_output")/.notices-XXXXXX")
trap 'rm -rf -- "$nudge_stage"' EXIT
cargo metadata --locked --offline --filter-platform "$(rustc -vV | sed -n 's/^host: //p')" --format-version 1 > "$nudge_stage/metadata.json"
mkdir "$nudge_stage/notices"
python3 scripts/package-notices.py --metadata "$nudge_stage/metadata.json" --sysroot "$(rustc --print sysroot)" --output "$nudge_stage/notices"
if [[ -e $nudge_output ]]; then
    [[ -f $nudge_output/THIRD_PARTY_NOTICES.md ]] || { printf 'Refusing to replace an unrecognized notices directory.\n' >&2; exit 1; }
    rm -rf -- "$nudge_output"
fi
mv -- "$nudge_stage/notices" "$nudge_output"
