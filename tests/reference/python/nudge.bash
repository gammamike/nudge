# Source in an interactive Bash 5+ shell. No DEBUG trap or history-policy changes.
[[ $- == *i* ]] || return 0
[[ ${_NUDGE_LOADED:-} == 1 ]] && return 0
if (( BASH_VERSINFO[0] < 5 )); then
    printf 'nudge requires Bash 5 or newer\n' >&2
    return 1
fi
_NUDGE_ROOT="$(builtin cd -- "$(command dirname -- "${BASH_SOURCE[0]}")" && builtin pwd)"
_NUDGE_LOADED=1
_NUDGE_LAST_HISTORY="$(HISTTIMEFORMAT= builtin history 1)"

_nudge_prompt() {
    local original_status=$? item line root
    local -a nudge_args=() nudge_options=()
    item="$(HISTTIMEFORMAT= builtin history 1)"
    if [[ $item == "$_NUDGE_LAST_HISTORY" ]]; then
        return "$original_status"
    fi
    _NUDGE_LAST_HISTORY=$item
    [[ ${NUDGE_ENABLED:-1} == 1 ]] || return "$original_status"
    (( original_status != 0 && original_status != 130 )) || return "$original_status"
    # History entry number followed by two spaces. Multiline/complex commands
    # are rejected by Python. Ignored/repeated history entries are skipped.
    [[ $item =~ ^[[:space:]]*[0-9]+[[:space:]]+(.*)$ ]] || return "$original_status"
    line=${BASH_REMATCH[1]}
    root=${line%% *}
    [[ $root == herdr || $root == omarchy ]] || return "$original_status"
    [[ $(type -t -- "$root") == file ]] || return "$original_status"
    [[ ${NUDGE_LOCAL_ONLY:-0} == 1 ]] && nudge_options+=(--local-only)
    mapfile -d '' -t nudge_args < <(
        command python3 "$_NUDGE_ROOT/nudge.py" confirm --command "$line" \
            --status "$original_status" "${nudge_options[@]}"
    )
    if (( ${#nudge_args[@]} )); then
        # The backend emits an absolute executable plus literal arguments.
        # No eval, no shell expansion, and no execution before Enter.
        command "${nudge_args[@]}"
        NUDGE_LAST_CORRECTION_STATUS=$?
    fi
    return "$original_status"
}

# Prepend without flattening array hooks; return the original status on decline.
if [[ $(declare -p PROMPT_COMMAND 2>/dev/null) == 'declare -a '* ]]; then
    PROMPT_COMMAND=(_nudge_prompt "${PROMPT_COMMAND[@]}")
else
    PROMPT_COMMAND=(_nudge_prompt "${PROMPT_COMMAND:-:}")
fi
