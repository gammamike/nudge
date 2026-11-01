#!/usr/bin/env python3
"""Paired process benchmarks. Never execute suggested commands."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import pty
import select
import signal
import statistics
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
PYTHON = ROOT / "tests/reference/python"
BACKENDS = {"python": [sys.executable, str(PYTHON / "nudge.py")],
            "rust": [str(ROOT / "target/release/nudge-rust")]}


def measure(backend, args, env):
    # wait4 supplies CPU timings. Its max RSS includes a launcher high-water
    # mark on this host; keep that raw field, but use memory_probe for memory.
    with tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile() as stderr, open(os.devnull) as stdin:
        actions = [(os.POSIX_SPAWN_DUP2, stdin.fileno(), 0),
                   (os.POSIX_SPAWN_DUP2, stdout.fileno(), 1),
                   (os.POSIX_SPAWN_DUP2, stderr.fileno(), 2)]
        argv = BACKENDS[backend] + args
        started = time.perf_counter_ns()
        pid = os.posix_spawn(argv[0], argv, env, file_actions=actions)
        try:
            _, status, usage = os.wait4(pid, 0)
        except BaseException:
            os.kill(pid, 9)
            os.waitpid(pid, 0)
            raise
        elapsed = (time.perf_counter_ns() - started) / 1_000_000
        stdout.seek(0)
        text = stdout.read().decode()
        result = None if args == ["--help"] else json.loads(text)
        code = os.WEXITSTATUS(status) if os.WIFEXITED(status) else -os.WTERMSIG(status)
        if code:
            raise RuntimeError(f"{backend} exited {code}")
        return {"backend": backend, "wall_ms": round(elapsed, 3),
                "cpu_ms": round((usage.ru_utime + usage.ru_stime) * 1000, 3),
                "max_rss_kib": usage.ru_maxrss, "result": result}


def stats(samples):
    summary = {"runs": len(samples)}
    for metric in ("wall_ms", "cpu_ms", "max_rss_kib"):
        values = sorted(s[metric] for s in samples)
        summary[metric] = {"median": round(statistics.median(values), 3),
                           "p95": values[math.ceil(len(values) * .95) - 1],
                           "min": values[0], "max": values[-1]}
    return summary


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def memory_probe(backend, env):
    pid, fd = pty.fork()
    if pid == 0:
        argv = BACKENDS[backend] + ["confirm", "--command", "herdr stop", "--local-only"]
        os.execve(argv[0], argv, env)
    output = b""
    try:
        deadline = time.monotonic() + 5
        while b"Any other key to cancel " not in output:
            if time.monotonic() > deadline:
                raise RuntimeError("confirmation prompt timed out")
            if select.select([fd], [], [], .05)[0]:
                output += os.read(fd, 65536)
        fields = {}
        for line in Path(f"/proc/{pid}/status").read_text().splitlines():
            if line.startswith(("VmRSS:", "VmHWM:")):
                key, value, _unit = line.split()
                fields[key.rstrip(":")] = int(value)
        os.write(fd, b"x")
        os.waitpid(pid, 0)
        return {"backend": backend, "rss_kib": fields["VmRSS"], "peak_rss_kib": fields["VmHWM"]}
    finally:
        try:
            os.kill(pid, signal.SIGKILL)
            os.waitpid(pid, 0)
        except ProcessLookupError:
            pass
        os.close(fd)


def add_memory(report, env):
    samples = []
    for iteration in range(10):
        for backend in (("python", "rust") if iteration % 2 == 0 else ("rust", "python")):
            samples.append(memory_probe(backend, env))
    report["memory"] = {"method": "Read /proc/PID/status VmRSS and VmHWM after each fresh process displays the local confirmation prompt. All prompts cancelled; no commands executed. This excludes inherited launcher high-water marks and Codex subprocesses.",
                        "samples": samples, "summary": {}}
    for backend in BACKENDS:
        selected = [s for s in samples if s["backend"] == backend]
        summary = {"runs": len(selected),
                   "median_rss_kib": statistics.median(s["rss_kib"] for s in selected),
                   "median_peak_rss_kib": statistics.median(s["peak_rss_kib"] for s in selected)}
        report["memory"]["summary"][backend] = summary
        print(backend, "direct process memory:", json.dumps(summary), flush=True)
    report["memory_note"] = "Do not compare group max_rss_kib values: wait4 includes a launcher high-water mark on this host. Use the separate /proc-based memory section. CPU measurements for refresh/AI include waited-for child work."


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--codex", action="store_true", help="12 live subscription-backed requests")
    parser.add_argument("--memory-only", action="store_true", help="append accurate memory readings to an existing report")
    parser.add_argument("--output", default=str(ROOT / "benchmarks/comparison-results.json"))
    args = parser.parse_args()
    env = dict(os.environ, NUDGE_CACHE_DIR=str(ROOT / ".cache/comparison"),
               NUDGE_MODEL="gpt-6-luna", NUDGE_CODEX_TIMEOUT="15")
    if args.memory_only:
        report = json.loads(Path(args.output).read_text())
        add_memory(report, env)
        Path(args.output).write_text(json.dumps(report, indent=2) + "\n")
        return
    report = {"measured_at_utc": datetime.now(timezone.utc).isoformat(),
              "platform": platform.platform(), "python": sys.version,
              "rustc": subprocess.check_output(["rustc", "--version"], text=True).strip(),
              "codex_model": "gpt-6-luna", "codex_reasoning_effort": "none",
              "method": "Fresh processes via posix_spawn/wait4. Paired alternating order; one shared metadata cache; warm OS file cache. Native release build, no cargo run. AI inputs/flags verified identical by parity tests. No corrections executed.",
              "memory_note": "See separate /proc memory readings; raw wait4 RSS includes launcher memory.",
              "rust_binary_bytes": Path(BACKENDS['rust'][0]).stat().st_size,
              "source_sha256": {str(path.relative_to(ROOT.parent)): digest(path)
                  for path in [PYTHON / 'nudge.py', ROOT / 'Cargo.lock', *sorted((ROOT / 'src').glob('*.rs'))]},
              "groups": {}}
    measure("python", ["refresh"], env)
    for backend in BACKENDS:
        measure(backend, ["suggest", "--local-only", "--command", "herdr stop"], env)
    cases = [("startup_help", ["--help"], 30, None, None),
             ("local_herdr", ["suggest", "--local-only", "--command", "herdr stop"], 30, "herdr server stop", "local"),
             ("local_omarchy_typo", ["suggest", "--local-only", "--command", "omarchy restart terminl"], 30, "omarchy restart terminal", "local"),
             ("local_omarchy_missing", ["suggest", "--local-only", "--command", "omarchy nightlight"], 30, "omarchy toggle nightlight", "local"),
             ("unsupported_command", ["suggest", "--local-only", "--command", "echo hello"], 30, None, "none"),
             ("metadata_refresh", ["refresh"], 5, None, None)]
    if args.codex:
        cases += [("codex_herdr", ["suggest", "--command", "herdr halt"], 3, "herdr server stop", "codex"),
                  ("codex_omarchy", ["suggest", "--command", "omarchy reload terminal"], 3, "omarchy restart terminal", "codex")]
    all_correct = True
    for name, options, count, expected, source in cases:
        samples = []
        for iteration in range(count):
            order = ("python", "rust") if iteration % 2 == 0 else ("rust", "python")
            for backend in order:
                sample = measure(backend, options, env)
                sample["pair"] = iteration
                if source:
                    sample["correct"] = (sample["result"]["suggestion"] == expected and sample["result"]["source"] == source)
                    all_correct &= sample["correct"]
                samples.append(sample)
        group = {"arguments": options, "samples": samples, "summary": {}}
        for backend in BACKENDS:
            selected = [s for s in samples if s["backend"] == backend]
            group["summary"][backend] = stats(selected)
            if source:
                group["summary"][backend]["correct"] = sum(s["correct"] for s in selected)
        py = group["summary"]["python"]["wall_ms"]["median"]
        native = group["summary"]["rust"]["wall_ms"]["median"]
        group["python_over_rust_wall_ratio"] = round(py / native, 2)
        report["groups"][name] = group
        Path(args.output).write_text(json.dumps(report, indent=2) + "\n")
        print(f"{name}: Python {py:.3f} ms, Rust {native:.3f} ms; ratio {py/native:.2f}x", flush=True)
    add_memory(report, env)
    Path(args.output).write_text(json.dumps(report, indent=2) + "\n")
    if not all_correct:
        raise SystemExit("One or more suggestions differed from the expected result; inspect samples.")


if __name__ == "__main__":
    main()
