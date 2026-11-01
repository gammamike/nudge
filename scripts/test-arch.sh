#!/usr/bin/env bash
# Build and install both AUR variants only inside a disposable Arch container.
set -euo pipefail
nudge_dist=$(realpath -- "${1:?usage: scripts/test-arch.sh DIST_DIRECTORY}")
nudge_repo=$(builtin cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && builtin pwd)
nudge_image=nudge-arch-test-$$-$RANDOM
nudge_container=
cleanup() {
    if [[ -n $nudge_container ]]; then docker rm -f "$nudge_container" >/dev/null 2>&1 || true; fi
    docker image rm "$nudge_image" >/dev/null 2>&1 || true
}
trap cleanup EXIT
docker build --pull -f "$nudge_repo/tests/Dockerfile.arch" -t "$nudge_image" "$nudge_repo/tests"
nudge_container=$(docker run -d --mount "type=bind,src=$nudge_repo,dst=/repo,readonly" \
    --mount "type=bind,src=$nudge_dist,dst=/dist,readonly" --tmpfs /work:exec \
    "$nudge_image" sleep infinity)
docker exec "$nudge_container" chown builder:builder /work
docker exec --user builder --env HOME=/home/builder "$nudge_container" bash /repo/tests/arch-package-smoke.sh build
docker exec "$nudge_container" bash /repo/tests/arch-package-smoke.sh install
