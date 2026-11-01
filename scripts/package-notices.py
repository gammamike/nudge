#!/usr/bin/env python3
"""Collect dependency and toolchain license notices for a binary bundle."""
import argparse
import json
from pathlib import Path
import shutil

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--metadata', type=Path, required=True)
parser.add_argument('--sysroot', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
metadata = json.loads(args.metadata.read_text())
licenses = args.output / 'licenses'
licenses.mkdir()
rows = []
for package in metadata['packages']:
    if package['id'] in metadata['workspace_members']:
        continue
    folder = Path(package['manifest_path']).parent
    files = {p for p in folder.iterdir() if p.is_file() and p.name.upper().startswith(('LICENSE', 'COPYING', 'NOTICE'))}
    if package.get('license_file'):
        files.add(folder / package['license_file'])
    if not files:
        raise SystemExit(f"No license file found for {package['name']}; review before distributing")
    name = f"{package['name']}-{package['version']}"
    target = licenses / name
    target.mkdir()
    for source in sorted(files):
        shutil.copyfile(source, target / source.name)
    rows.append(f"| {name} | {package['license']} |")
rust_docs = args.sysroot / 'share/doc/rust'
# Preserve the toolchain's full notice inventory, including native musl components.
shutil.copyfile(rust_docs / 'COPYRIGHT.html', licenses / 'RUST-COPYRIGHT.html')
shutil.copytree(rust_docs / 'licenses', licenses / 'rust')
(args.output / 'THIRD_PARTY_NOTICES.md').write_text(
    '# Third-party notices\n\n'
    'Dependency license files are included under `licenses/`. Rust toolchain and\n'
    'native-library notices are in `licenses/RUST-COPYRIGHT.html` and `licenses/rust/`.\n'
    'This inventory includes build dependencies as well as runtime dependencies.\n\n'
    '| Package | Declared license expression |\n|---|---|\n' + '\n'.join(rows) + '\n')
