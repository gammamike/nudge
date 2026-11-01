[[ -f ~/.bashrc ]] && source ~/.bashrc
source "$(command dirname -- "${BASH_SOURCE[0]}")/nudge.bash"
printf '\nNudge active in this shell. Run exit to return.\n'
printf 'Disable AI: export NUDGE_LOCAL_ONLY=1\n\n'
