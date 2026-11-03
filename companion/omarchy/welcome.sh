#!/bin/bash
# Remember that the welcome panel was displayed; never install or contact a provider.
set -euo pipefail
(( $# == 1 )) || exit 1
state_home=${XDG_STATE_HOME:-}
[[ $state_home == /* ]] || state_home=$HOME/.local/state
marker=$state_home/nudge/companion-welcome-seen
case "$1" in
  status)
    if [[ -e $marker || -L $marker ]]; then printf '{"seen":true}\n'; else printf '{"seen":false}\n'; fi
    ;;
  mark)
    umask 077
    mkdir -p -- "$marker"
    ;;
  *) exit 1 ;;
esac
