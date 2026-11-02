#!/usr/bin/env bash
# Invoked only inside a disposable Arch userspace; never on the development host.
set -euo pipefail
case ${1:-} in
build)
    mkdir -p /work/downloads
    cp /dist/*.tar.gz /work/downloads/
    python3 /repo/scripts/prepare-aur.py --dist /dist --output /work/aur "${@:2}"
    for package in nudge-bash nudge-bash-bin; do
        (
            cd "/work/aur/$package"
            SRCDEST=/work/downloads makepkg --cleanbuild --force --noconfirm
            namcap PKGBUILD ./"$package"-[0-9]*.pkg.tar.zst | tee /work/"$package"-namcap.log
            if grep -q ' E: ' /work/"$package"-namcap.log; then exit 1; fi
        )
    done
    # A packaging-only revision exercises pacman's real upgrade path.
    (
        cd /work/aur/nudge-bash-bin
        cp PKGBUILD /work/bin-original.PKGBUILD
        sed -i 's/^pkgrel=1$/pkgrel=2/' PKGBUILD
        SRCDEST=/work/downloads makepkg --repackage --force --noconfirm
        mkdir -p /work/upgrade
        mv ./nudge-bash-bin-*-2-*.pkg.tar.zst /work/upgrade/
        mv /work/bin-original.PKGBUILD PKGBUILD
    )
    ;;
install)
    # Root is confined to the disposable userspace running this script.
    [[ $EUID == 0 && -d /work/aur && -r /repo/Makefile ]]
    mkdir -p /home/builder/.config/nudge
    printf 'keep settings\n' > /home/builder/.config/nudge/preserve-test
    printf '# preserve shell\n' > /home/builder/.bashrc
    for package in nudge-bash nudge-bash-bin; do
        pacman -U --noconfirm /work/aur/"$package"/"$package"-[0-9]*.pkg.tar.zst
        pacman -Qk "$package"
        nudge-bash --version
        [[ $(nudge-bash supported | wc -l) -ge 267 ]]
        HOME=/home/builder bash --noprofile --norc -ic 'source /usr/lib/nudge-bash/nudge.bash; [[ $_NUDGE_LOADED == 1 ]]'
        if nudge-bash uninstall; then exit 1; fi
        pacman -U --noconfirm /work/aur/"$package"/"$package"-[0-9]*.pkg.tar.zst
        if [[ $package == nudge-bash-bin ]]; then
            cmp /usr/lib/nudge-bash/bin/nudge /work/aur/nudge-bash-bin/src/nudge-*-linux-x86_64/bin/nudge
            pacman -U --noconfirm /work/upgrade/*.pkg.tar.zst
            [[ $(pacman -Q nudge-bash-bin) == *-2 ]]
        fi
        pacman -R --noconfirm "$package"
        [[ ! -e /usr/bin/nudge-bash && ! -e /usr/lib/nudge-bash ]]
        [[ $(cat /home/builder/.config/nudge/preserve-test) == 'keep settings' ]]
        [[ $(cat /home/builder/.bashrc) == '# preserve shell' ]]
    done
    printf 'PASS: source and binary Arch packages; install, reinstall, upgrade, hook, lifecycle guard, removal, settings preservation\n'
    ;;
*) printf 'usage: arch-package-smoke.sh build [--allow-development] | install\n' >&2; exit 1 ;;
esac
