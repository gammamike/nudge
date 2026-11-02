#!/usr/bin/env bash
# Run inside a disposable Linux userspace with /bundle containing an extracted archive.
set -euo pipefail
export NUDGE_LOCAL_ONLY=1 HISTFILE=/dev/null
nudge_test_home=$(mktemp -d)
# HOME is set only for child processes so the test's real home is never modified.
printf '# retain this setting\nexport DISTRO_SETTING=retained\n' > "$nudge_test_home/.bashrc"
cp "$nudge_test_home/.bashrc" "$nudge_test_home/original.bashrc"
env HOME="$nudge_test_home" /bundle/install.sh
nudge_installed=$nudge_test_home/.local/bin/nudge
[[ -x $nudge_installed ]]
env HOME="$nudge_test_home" "$nudge_installed" --version
env HOME="$nudge_test_home" "$nudge_installed" supported > "$nudge_test_home/supported"
/bundle/bin/nudge supported > "$nudge_test_home/expected-supported"
[[ $(sha256sum < "$nudge_test_home/supported") == $(sha256sum < "$nudge_test_home/expected-supported") ]]
[[ $(wc -l < "$nudge_test_home/supported") -ge 120 ]]
# A second install must not duplicate the hook or create another release.
env HOME="$nudge_test_home" /bundle/install.sh
[[ $(grep -c '^# >>> nudge managed setup >>>$' "$nudge_test_home/.bashrc") == 1 ]]
[[ $(find "$nudge_test_home/.local/share/nudge/releases" -mindepth 1 -maxdepth 1 -type d | wc -l) == 1 ]]
# Simulate a second build without executing any real corrected operation.
cp /bundle/bin/nudge "$nudge_test_home/update"
printf '\nsmoke-test update\n' >> "$nudge_test_home/update"
env HOME="$nudge_test_home" "$nudge_test_home/update" install
nudge_current=$(readlink "$nudge_test_home/.local/share/nudge/current")
env HOME="$nudge_test_home" "$nudge_installed" rollback
[[ $(readlink "$nudge_test_home/.local/share/nudge/current") != "$nudge_current" ]]
mkdir "$nudge_test_home/mocks"
cat > "$nudge_test_home/mocks/git" <<'MOCK'
#!/usr/bin/env bash
case "$*" in
    --list-cmds=main,others,alias) printf 'status\n' ;;
    'status -h') printf 'usage: git status\n'; exit 129 ;;
    *) exit 2 ;;
esac
MOCK
chmod +x "$nudge_test_home/mocks/git"
env HOME="$nudge_test_home" PATH="$nudge_test_home/mocks:$PATH" "$nudge_installed" suggest --local-only --command 'git statsu' > "$nudge_test_home/result"
grep -q '"suggestion": "git status"' "$nudge_test_home/result"
# Interactive Bash loads the installed hook while retaining user settings.
env HOME="$nudge_test_home" bash --noprofile --rcfile "$nudge_test_home/.bashrc" -ic '[[ $_NUDGE_LOADED == 1 && $DISTRO_SETTING == retained && ${PROMPT_COMMAND[0]} == _nudge_prompt ]]'
mkdir -p "$nudge_test_home/.config/nudge"
printf 'keep settings\n' > "$nudge_test_home/.config/nudge/keep"
env HOME="$nudge_test_home" "$nudge_installed" uninstall
read -r nudge_before nudge_digest_file < <(sha256sum "$nudge_test_home/original.bashrc")
read -r nudge_after nudge_digest_file < <(sha256sum "$nudge_test_home/.bashrc")
[[ $nudge_before == "$nudge_after" ]]
[[ ! -e $nudge_installed && ! -e $nudge_test_home/.local/share/nudge ]]
[[ -f $nudge_test_home/.config/nudge/keep && -d $nudge_test_home/.cache/nudge ]]
printf 'PASS: %s; Bash %s; %s\n' "$(. /etc/os-release; printf '%s' "$PRETTY_NAME")" "$BASH_VERSION" "$(uname -m)"
