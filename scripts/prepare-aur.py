#!/usr/bin/env python3
"""Render checksum-pinned AUR recipes locally; never submit or install them."""
import argparse
import importlib.util
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('verify_release', ROOT / 'scripts/verify-release.py')
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dist', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--allow-development', action='store_true', help='local package tests only')
    args = parser.parse_args()
    version, checksums = release.verify(args.dist, allow_development=args.allow_development)
    # This recipe is for stable versions; prereleases need an explicit Arch version policy.
    if '-' in version:
        parser.error('AUR recipes currently require a stable x.y.z release')
    if args.output.exists():
        parser.error('Output directory already exists; choose a new directory')
    args.output.mkdir(parents=True)
    for kind, name, archive in [
        ('source', 'nudge-bash', f'nudge-{version}-source.tar.gz'),
        ('bin', 'nudge-bash-bin', f'nudge-{version}-linux-x86_64.tar.gz'),
    ]:
        destination = args.output / name
        destination.mkdir()
        template = (ROOT / f'packaging/aur/PKGBUILD.{kind}.in').read_text()
        text = template.replace('@VERSION@', version).replace('@SHA256@', checksums[archive])
        if args.allow_development:
            text = '# LOCAL DEVELOPMENT TEST ONLY; DO NOT SUBMIT\n' + text
        (destination / 'PKGBUILD').write_text(text)
        result = subprocess.run(['makepkg', '--printsrcinfo'], cwd=destination, check=True, capture_output=True, text=True)
        (destination / '.SRCINFO').write_text(result.stdout)
    print(f'Prepared {args.output}; review before submitting to AUR')


if __name__ == '__main__':
    main()
