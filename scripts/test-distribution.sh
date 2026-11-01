#!/usr/bin/env bash
# Run the packaged installer as an unprivileged user in one disposable Linux image.
set -euo pipefail
nudge_archive=${1:?usage: scripts/test-distribution.sh ARCHIVE IMAGE}
nudge_image=${2:?missing container image}
[[ $nudge_image =~ ^[a-zA-Z0-9][a-zA-Z0-9./:_@-]+$ ]] || exit 1
nudge_repo=$(builtin cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && builtin pwd)
nudge_stage=$(mktemp -d)
nudge_tag=nudge-smoke-$$-$RANDOM
cleanup() {
    docker image rm "$nudge_tag" >/dev/null 2>&1 || true
    rm -rf -- "$nudge_stage"
}
trap cleanup EXIT
(
    builtin cd -- "$(dirname -- "$nudge_archive")"
    sha256sum -c SHA256SUMS
)
tar -xzf "$nudge_archive" -C "$nudge_stage"
nudge_bundle=$(find "$nudge_stage" -mindepth 1 -maxdepth 1 -type d)
[[ -x $nudge_bundle/bin/nudge ]]
mkdir "$nudge_stage/build"
cp "$nudge_repo/tests/Dockerfile.smoke" "$nudge_stage/build/Dockerfile"
docker build --pull --build-arg "BASE=$nudge_image" -t "$nudge_tag" "$nudge_stage/build"
docker run --rm --network none --cap-drop ALL --security-opt no-new-privileges --user 1000:1000 \
    --mount "type=bind,src=$nudge_bundle,dst=/bundle,readonly" \
    --mount "type=bind,src=$nudge_repo/tests/distribution-smoke.sh,dst=/smoke.sh,readonly" \
    "$nudge_tag" /bin/bash /smoke.sh
