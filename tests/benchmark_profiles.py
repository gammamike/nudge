#!/usr/bin/env python3
"""Time suggestions against installed tools; never execute a corrected command."""
import argparse
import json
import math
import os
from pathlib import Path
import statistics
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--samples', type=int, default=25)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.samples < 2:
        parser.error('--samples must be at least 2')
    cases = json.loads((ROOT / 'tests/fixtures/linux-profile-cases.json').read_text())
    results = {}
    base = {k:v for k,v in os.environ.items() if not k.startswith('NUDGE_')}
    with tempfile.TemporaryDirectory(prefix='nudge-profile-benchmark-') as directory:
        for name, case in cases.items():
            env = dict(base, NUDGE_CONFIG=directory+'/config.json', NUDGE_CACHE_DIR=directory+'/'+name)
            rows = []
            for _ in range(args.samples + 1):
                started = time.perf_counter()
                process = subprocess.run([str(ROOT/'target/release/nudge-rust'), 'suggest', '--command', case['input'], '--local-only'], capture_output=True, text=True, env=env, timeout=10, check=True)
                elapsed = (time.perf_counter()-started)*1000
                result = json.loads(process.stdout)
                if result.get('argv') != case['argv']:
                    raise RuntimeError(f'{name}: unexpected suggestion: {result}')
                rows.append((elapsed, result['elapsed_ms']))
            warm = sorted(row[0] for row in rows[1:])
            results[name] = {'command':case['input'], 'cold_process_ms':round(rows[0][0],3),
                             'warm_process_p50_ms':round(statistics.median(warm),3),
                             'warm_process_p95_ms':round(warm[math.ceil(len(warm)*.95)-1],3),
                             'warm_engine_p50_ms':round(statistics.median(row[1] for row in rows[1:]),3)}
    output = {'samples_per_tool':args.samples, 'tools':len(results),
              'scope':'One empty-cache suggestion, then warm suggestions; includes process launch. No failed-command execution, Bash prompt rendering, user confirmation or AI latency.',
              'results':results}
    args.output.write_text(json.dumps(output,indent=2)+'\n')
    print(json.dumps({'tools':len(results), 'warm_p50_median_ms':round(statistics.median(r['warm_process_p50_ms'] for r in results.values()),3),
                      'warm_p50_range_ms':[min(r['warm_process_p50_ms'] for r in results.values()),max(r['warm_process_p50_ms'] for r in results.values())]}))


if __name__ == '__main__':
    main()
