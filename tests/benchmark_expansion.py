#!/usr/bin/env python3
"""Measure local suggestions from each expansion batch without executing them."""
import argparse
import json
import os
from pathlib import Path
import statistics
import subprocess
import tempfile
import time

from support import BINARY, ROOT


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--samples', type=int, default=25)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    if args.samples < 1:
        parser.error('--samples must be positive')
    cases = json.loads((ROOT / 'tests/fixtures/expansion-cases.json').read_text())
    results = []
    selected = {}
    for name, case in cases.items():
        selected.setdefault(case['batch'], (name, case['positive'][0]))
    with tempfile.TemporaryDirectory(prefix='nudge-benchmark-') as home:
        Path(home, 'runtime').mkdir(mode=0o700)
        env = {key: os.environ[key] for key in ('PATH', 'LD_LIBRARY_PATH', 'PYTHONPATH', 'PERL5LIB') if key in os.environ}
        env.update(HOME=home, XDG_CONFIG_HOME=home + '/config', XDG_CACHE_HOME=home + '/cache',
                   XDG_DATA_HOME=home + '/data', XDG_RUNTIME_DIR=home + '/runtime',
                   NUDGE_CONFIG=home + '/nudge.json', LC_ALL='C', TERM='dumb', NO_COLOR='1', PAGER='cat')
        for batch, (name, case) in selected.items():
            env['NUDGE_CACHE_DIR'] = home + '/cache/' + name
            samples = []
            for _ in range(args.samples + 1):
                start = time.perf_counter()
                result = subprocess.run([str(BINARY), 'suggest', '--local-only', '--command', case['input']],
                                        env=env, cwd=home, capture_output=True, text=True, check=True)
                wall = (time.perf_counter() - start) * 1000
                value = json.loads(result.stdout)
                if value.get('argv') != case['argv']:
                    raise RuntimeError(f'{name}: metadata correction failed: {value}')
                samples.append((value['elapsed_ms'], wall))
            warm = samples[1:]
            results.append(dict(batch=batch, command=case['input'], samples=args.samples,
                                cold_engine_ms=samples[0][0],
                                warm_engine_median_ms=statistics.median(v[0] for v in warm),
                                warm_wall_median_ms=statistics.median(v[1] for v in warm)))
    args.output.write_text(json.dumps(results, indent=2) + '\n')


if __name__ == '__main__':
    main()
