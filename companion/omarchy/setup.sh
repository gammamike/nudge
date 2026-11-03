#!/bin/bash
# Explicit first-run setup: verify a release, install the CLI/hook, then the shortcut.
set -euo pipefail
export LC_ALL=C
umask 077
unset TAR_OPTIONS

fail() { printf '%s\n' "$*" >&2; exit 1; }
(( $# == 0 )) || fail 'Setup takes no arguments'
[[ $(uname -s) == Linux && $(uname -m) == x86_64 ]] ||
  fail 'Guided setup supports Linux x86_64. See the installation guide for source builds.'
(( BASH_VERSINFO[0] >= 5 )) || fail 'Bash 5 or newer is required'
for dependency in jq curl tar gzip sha256sum timeout flock mktemp mkdir chmod cmp ln rm cat; do
  command -v "$dependency" >/dev/null || fail "Missing dependency: $dependency"
done
companion_dir=$(builtin cd -- "${BASH_SOURCE[0]%/*}" && builtin pwd)
/bin/bash "$companion_dir/launcher.sh" check
state_home=${XDG_STATE_HOME:-}
[[ $state_home == /* ]] || state_home=$HOME/.local/state
mkdir -p -- "$state_home/nudge"
exec 9> "$state_home/nudge/setup.lock"
flock -n 9 || fail 'Nudge setup is already running'
data_home=${XDG_DATA_HOME:-}
[[ $data_home == /* ]] || data_home=$HOME/.local/share
managed=$data_home/nudge

if [[ -x $managed/current/bin/nudge && -f $managed/install.json ]] &&
    jq -e '.format == 1' "$managed/install.json" >/dev/null; then
  # Reuse the installed version and let its installer safely restore the hook.
  timeout --kill-after=2s 30s "$managed/current/bin/nudge" install >&2
else
  if type -P nudge-bash >/dev/null; then
    fail 'Nudge is already installed through a package or custom path. Follow the package Bash activation instructions; guided setup will not replace it.'
  fi
  for prefix in "$HOME/.local" /usr/local /usr; do
    [[ ! -x $prefix/lib/nudge-bash/bin/nudge ]] ||
      fail 'A package installation exists. Follow its Bash activation instructions; guided setup will not replace it.'
  done
  version=$(jq -er '.version | select(test("^[0-9]+\\.[0-9]+\\.[0-9]+$"))' "$companion_dir/../../manifest.json")
  name=nudge-$version-linux-x86_64
  base=https://github.com/gammamike/nudge/releases/download/v$version
  stage=$(mktemp -d)
  trap 'rm -rf -- "$stage"' EXIT
  download() {
    curl --disable --fail --location --silent --show-error --proto '=https' --proto-redir '=https' \
      --connect-timeout 15 --max-time 120 --max-filesize "$3" --output "$2" "$1"
  }
  printf 'Downloading Nudge %s from its GitHub release…\n' "$version" >&2
  download "$base/SHA256SUMS" "$stage/SHA256SUMS" 16384 ||
    fail 'Could not download release checksums. Check your connection or retry after the release is available.'
  expected=
  while read -r digest filename extra; do
    if [[ $filename == "$name.tar.gz" ]]; then
      [[ -z $expected && $digest =~ ^[a-f0-9]{64}$ && -z $extra ]] || fail 'Invalid release checksum entry'
      expected=$digest
    fi
  done < "$stage/SHA256SUMS"
  [[ -n $expected ]] || fail 'The release does not contain the expected Linux archive'
  download "$base/$name.tar.gz" "$stage/bundle.tar.gz" 33554432 || fail 'Could not download the Nudge release. No installation changes were made.'
  read -r actual _ < <(sha256sum "$stage/bundle.tar.gz")
  [[ $actual == "$expected" ]] || fail 'Release checksum mismatch. Nothing was installed.'
  # Reject links, special files, traversal, and unexpected names before extraction.
  entries=$(tar -tzf "$stage/bundle.tar.gz") || fail 'Invalid release archive'
  count=0
  while IFS= read -r entry; do
    [[ $entry == "$name/"* && $entry =~ ^[a-zA-Z0-9_./+-]+$ && /$entry/ != */../* && /$entry/ != */./* ]] || fail 'Unsafe release archive path'
    (( ++count <= 2048 )) || fail 'Too many release archive entries'
  done <<< "$entries"
  types=$(tar -tvzf "$stage/bundle.tar.gz") || fail 'Invalid release archive'
  while IFS= read -r entry; do
    [[ ${entry:0:1} == - || ${entry:0:1} == d ]] || fail 'Release archive contains a link or special file'
  done <<< "$types"
  tar --extract --gzip --file "$stage/bundle.tar.gz" --directory "$stage" --no-same-owner --no-same-permissions
  binary=$stage/$name/bin/nudge
  [[ -f $binary && ! -L $binary ]] || fail 'Release executable is missing'
  chmod 700 "$binary"
  [[ $(timeout 5s "$binary" --version) == "nudge $version" ]] || fail 'Release version mismatch'
  timeout --kill-after=2s 30s "$binary" install >&2
fi
if ! /bin/bash "$companion_dir/launcher.sh" install >/dev/null; then
  fail 'Nudge and its Bash hook were installed, but the launcher could not be added. Use Add launcher shortcut to retry.'
fi
printf '{"installed":true}\n'
