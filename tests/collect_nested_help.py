#!/usr/bin/env python3
"""Capture fixed metadata queries from the reviewed nested Linux registry."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def queries(node):
    if 'help' in node:
        yield node['help']
    yield from node.get('extra_help', [])
    for child in node.get('commands', {}).values():
        yield from queries(child)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bin-dir', type=Path, help='directory of Linux executables; otherwise use PATH')
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--tool', action='append', help='capture only this executable; repeatable')
    args = parser.parse_args()
    profiles = json.loads((ROOT / 'data/nested-profiles.json').read_text())
    captured = {}
    with tempfile.TemporaryDirectory(prefix='nudge-help-') as home:
        Path(f'{home}/runtime').mkdir(mode=0o700)
        env = {key: os.environ[key] for key in ('PATH', 'LD_LIBRARY_PATH', 'PYTHONPATH', 'PERL5LIB') if key in os.environ}
        env.update(HOME=home, XDG_CONFIG_HOME=f'{home}/config', XDG_DATA_HOME=f'{home}/data',
                   XDG_RUNTIME_DIR=f'{home}/runtime', XDG_CACHE_HOME=f'{home}/cache', PAGER='cat', MANPAGER='cat',
                   NIX_PAGER='cat', LC_ALL='C', TERM='dumb', NO_COLOR='1')
        if args.tool and set(args.tool) - profiles.keys():
            parser.error('unknown executable in --tool')
        for name, profile in profiles.items():
            if args.tool and name not in args.tool:
                continue
            executable = str(args.bin_dir.resolve() / name) if args.bin_dir else shutil.which(name)
            if not executable:
                parser.error(f'{name} is unavailable')
            captured[name] = {}
            for query in queries(profile['root']):
                # Kubectl separates global options from ordinary command help.
                if query != ['__dump-cli'] and not (name == 'kubectl' and query == ['options']) and query[-1] != '--help':
                    raise ValueError(f'not a metadata query: {query}')
                result = subprocess.run([executable, *query], env=env, stdin=subprocess.DEVNULL,
                                        capture_output=True, text=True, timeout=10, check=True)
                captured[name][json.dumps(query, separators=(',', ':'))] = {
                    'status': result.returncode,
                    'stdout': result.stdout.replace(home, '/home/example'),
                    'stderr': result.stderr.replace(home, '/home/example'),
                }
    args.output.write_text(json.dumps(captured, indent=2) + '\n')


if __name__ == '__main__':
    main()
