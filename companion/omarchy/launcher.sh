#!/bin/bash
# Manage only the companion's per-user application shortcut, on explicit request.
set -euo pipefail

fail() {
  printf '%s\n' "$*" >&2
  exit 1
}

(( $# == 1 )) || fail 'Usage: launcher.sh install | remove | status'
case "$1" in install|remove|status) ;; *) fail 'Unknown launcher action' ;; esac

directory=${BASH_SOURCE[0]%/*}
[[ $directory != "${BASH_SOURCE[0]}" ]] || directory=.
template=$directory/gammamike.nudge.desktop
data_home=${XDG_DATA_HOME:-}
if [[ $data_home != /* ]]; then
  [[ ${HOME:-} == /* ]] || fail 'An absolute HOME or XDG_DATA_HOME is required'
  data_home=$HOME/.local/share
fi
applications=$data_home/applications
destination=$applications/gammamike.nudge.desktop

owned() {
  [[ -f $destination && ! -L $destination ]] && cmp -s -- "$template" "$destination"
}

if [[ $1 == status ]]; then
  if owned; then printf '{"installed":true}\n'; else printf '{"installed":false}\n'; fi
  exit 0
fi

if [[ -e $destination || -L $destination ]]; then
  owned || fail 'The Nudge launcher file was modified or belongs to another installation; left unchanged.'
fi

case "$1" in
  install)
    if [[ ! -e $destination ]]; then
      mkdir -p -- "$applications"
      temporary=$(mktemp "$applications/.nudge-launcher-XXXXXX")
      trap 'rm -f -- "$temporary"' EXIT
      cat -- "$template" > "$temporary"
      chmod 644 -- "$temporary"
      # A hard link publishes the complete file without replacing a racing writer.
      ln -T -- "$temporary" "$destination"
    fi
    printf '{"installed":true}\n'
    ;;
  remove)
    rm -f -- "$destination"
    printf '{"installed":false}\n'
    ;;
esac
