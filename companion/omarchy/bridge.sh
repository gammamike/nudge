#!/bin/bash
# Adapt the settings panel to the installed CLI; never evaluate input as code.
set -euo pipefail
nudge_time_limit=15s
companion_dir=${BASH_SOURCE[0]%/*}
[[ $companion_dir != "${BASH_SOURCE[0]}" ]] || companion_dir=.

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
  timeout --signal=TERM --kill-after=2s "$nudge_time_limit" "$binary" "$@"
}

status() {
  local launcher_status
  launcher_status=$(/bin/bash "$companion_dir/launcher.sh" status)
  if [[ -z $binary ]]; then
    jq -cn --argjson launcher "$launcher_status" '{available: false, launcher: $launcher}'
    return
  fi
  local settings
  settings=$(invoke config)
  jq -en --arg binary "$binary" --argjson settings "$settings" --argjson launcher "$launcher_status" '
    if ($settings.config | type) == "object" and
       ($settings.path | type) == "string" and
       ($settings.provider | type) == "string"
    then {available: true, binary: $binary, settings: $settings, launcher: $launcher}
    else error("Unsupported Nudge configuration response; update Nudge") end'
}

action=${1:-}
(( $# > 0 )) && shift
case "$action" in
  setup)
    (( $# == 0 )) || fail 'Setup takes no arguments'
    timeout --signal=TERM --kill-after=5s 300s /bin/bash "$companion_dir/setup.sh" >/dev/null
    # Rediscover the newly installed executable in a fresh invocation.
    exec /bin/bash "${BASH_SOURCE[0]}" status
    ;;
  launcher-install|launcher-remove)
    (( $# == 0 )) || fail 'Launcher actions take no arguments'
    /bin/bash "$companion_dir/launcher.sh" "${action#launcher-}"
    ;;
  status)
    (( $# == 0 )) || fail 'status takes no arguments'
    status
    ;;
  save|test|models)
    if [[ $action == save || $action == test ]]; then
      (( $# == 3 )) || fail 'save/test requires provider, model, and endpoint'
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
      if [[ $action == test ]]; then
        args=(check-provider --provider "$provider")
        nudge_time_limit=25s
        export NUDGE_AI_TIMEOUT=15
      else
        args=(config --provider "$provider")
      fi
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
  *) fail 'Usage: bridge.sh status | setup | launcher-install | launcher-remove | save PROVIDER MODEL ENDPOINT | test PROVIDER MODEL ENDPOINT | models PROVIDER ENDPOINT' ;;
esac
