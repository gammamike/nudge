# Source in an interactive Bash 5+ shell. No DEBUG trap or history-policy changes.
[[ $- == *i* ]] || return 0
[[ $OSTYPE == linux* ]] || return 0
[[ ${_NUDGE_LOADED:-} == 1 ]] && return 0
if (( BASH_VERSINFO[0] < 5 )); then
    printf 'nudge requires Bash 5 or newer\n' >&2
    return 1
fi
_NUDGE_ROOT=${BASH_SOURCE[0]}
if [[ $_NUDGE_ROOT == */* ]]; then
    _NUDGE_ROOT=${_NUDGE_ROOT%/*}
else
    _NUDGE_ROOT=.
fi
_NUDGE_ROOT="$(builtin cd -- "${_NUDGE_ROOT:-/}" && builtin pwd)"
_NUDGE_LOADED=1
declare -gA _NUDGE_EXECUTABLES=()
while IFS= read -r _nudge_name; do
    [[ $_nudge_name =~ ^[a-zA-Z0-9][a-zA-Z0-9_-]*$ ]] && _NUDGE_EXECUTABLES["$_nudge_name"]=1
done < <(command "$_NUDGE_ROOT/target/release/nudge-rust" supported)
unset _nudge_name
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
    # are rejected by the backend. Ignored/repeated history entries are skipped.
    [[ $item =~ ^[[:space:]]*[0-9]+[[:space:]]+(.*)$ ]] || return "$original_status"
    line=${BASH_REMATCH[1]}
    [[ $line =~ ^([a-zA-Z0-9][a-zA-Z0-9_-]*)([[:space:]]|$) ]] || return "$original_status"
    root=${BASH_REMATCH[1]}
    [[ ${_NUDGE_EXECUTABLES[$root]:-0} == 1 ]] || return "$original_status"
    [[ $(type -t -- "$root") == file ]] || return "$original_status"
    [[ ${NUDGE_LOCAL_ONLY:-0} == 1 ]] && nudge_options+=(--local-only)
    mapfile -d '' -t nudge_args < <(
        command "$_NUDGE_ROOT/target/release/nudge-rust" confirm --command "$line" \
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
