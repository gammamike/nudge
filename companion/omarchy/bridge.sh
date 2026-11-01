#!/bin/bash
# Adapt the settings panel to the installed CLI; never evaluate input as code.
set -euo pipefail

fail() {
  printf '%s\n' "$*" >&2
  exit 1
}

for dependency in jq timeout; do
  command -v "$dependency" >/dev/null || fail "Missing dependency: $dependency"
done

binary=$(type -P nudge-bash || true)
if [[ -z $binary ]]; then
  data_home=${XDG_DATA_HOME:-}
  [[ $data_home == /* ]] || data_home=$HOME/.local/share
  data_dir=$data_home/nudge
  if [[ -x $data_dir/current/bin/nudge && -f $data_dir/install.json ]] &&
    jq -e '.format == 1' "$data_dir/install.json" >/dev/null 2>&1; then
    binary=$data_dir/current/bin/nudge
  else
    for prefix in "$HOME/.local" /usr/local /usr; do
      if [[ -x $prefix/lib/nudge-bash/bin/nudge ]]; then
        binary=$prefix/lib/nudge-bash/bin/nudge
        break
      fi
    done
  fi
fi

# An unrelated program can also be named nudge. Only use the package command
# or Nudge's known installation layouts, never a bare `nudge` found on PATH.
invoke() {
  [[ -n $binary ]] || fail 'Nudge is not installed. See the Setup tab.'
  timeout --signal=TERM --kill-after=2s 15s "$binary" "$@"
}

status() {
  if [[ -z $binary ]]; then
    printf '{"available":false}\n'
    return
  fi
  local settings
  settings=$(invoke config)
  jq -en --arg binary "$binary" --argjson settings "$settings" '
    if ($settings.config | type) == "object" and
       ($settings.path | type) == "string" and
       ($settings.provider | type) == "string"
    then {available: true, binary: $binary, settings: $settings}
    else error("Unsupported Nudge configuration response; update Nudge") end'
}

action=${1:-}
(( $# > 0 )) && shift
case "$action" in
  status)
    (( $# == 0 )) || fail 'status takes no arguments'
    status
    ;;
  save|models)
    if [[ $action == save ]]; then
      (( $# == 3 )) || fail 'save requires provider, model, and endpoint'
      provider=$1 model=$2 endpoint=$3
    else
      (( $# == 2 )) || fail 'models requires provider and endpoint'
      provider=$1 endpoint=$2
    fi
    case "$provider" in
      codex|claude|ollama|local) ;;
      *) fail 'Unknown provider' ;;
    esac
    if [[ $action == models ]]; then
      [[ $provider == ollama || $provider == local ]] ||
        fail 'Model discovery is available for local providers only'
      args=(models --provider "$provider")
    else
      args=(config --provider "$provider")
      [[ -z $model ]] || args+=(--model "$model")
    fi
    if [[ -n $endpoint ]]; then
      [[ $provider == ollama || $provider == local ]] ||
        fail 'Endpoints apply to local providers only'
      args+=(--endpoint "$endpoint")
    fi
    if [[ $action == save ]]; then
      invoke "${args[@]}" >/dev/null
      status
    else
      invoke "${args[@]}"
    fi
    ;;
  *) fail 'Usage: bridge.sh status | save PROVIDER MODEL ENDPOINT | models PROVIDER ENDPOINT' ;;
esac
