#!/usr/bin/env python3
"""Compare both real launchers and installed Omarchy. Cancel every correction."""
import json
import os
from pathlib import Path
import pty
import select
import signal
import statistics
import time

ROOT = Path(__file__).resolve().parents[1]
READY = b"\x1b[?2004h__COMPARE__ "


class TrialShell:
    def __init__(self, launcher):
        self.pid, self.fd = pty.fork()
        if self.pid == 0:
            env = dict(os.environ, HISTFILE="/dev/null", NUDGE_LOCAL_ONLY="1", TERM="xterm-256color")
            os.execve(str(launcher), [str(launcher)], env)
        self.pending = b""
        try:
            self.until(b"Disable AI: export NUDGE_LOCAL_ONLY=1")
            os.write(self.fd, b'HISTFILE=/dev/null; _comparison_prompt() { PS1="__COMPARE__ "; }; PROMPT_COMMAND+=(_comparison_prompt)\n')
            self.until(READY)
        except BaseException:
            self.close()
            raise

    def until(self, marker):
        deadline = time.monotonic() + 8
        while marker not in self.pending:
            if time.monotonic() > deadline:
                raise RuntimeError(f"missing {marker!r}: {self.pending[-800:]!r}")
            if select.select([self.fd], [], [], .05)[0]:
                self.pending += os.read(self.fd, 65536)
        end = self.pending.index(marker) + len(marker)
        output, self.pending = self.pending[:end], self.pending[end:]
        return output

    def measure(self):
        # Separate repeated commands so ignoredups does not suppress the hook.
        os.write(self.fd, b":\n")
        self.until(READY)
        started = time.perf_counter_ns()
        os.write(self.fd, b"omarchy theme lsit\n")
        output = self.until(b"Any other key to cancel ")
        elapsed = (time.perf_counter_ns() - started) / 1_000_000
        if b"omarchy theme list" not in output:
            raise RuntimeError("incorrect correction")
        os.write(self.fd, b"x")
        self.until(READY)
        return round(elapsed, 3)

    def close(self):
        try:
            os.kill(self.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        os.waitpid(self.pid, 0)
        os.close(self.fd)


def main():
    shells = {}
    try:
        shells["python"] = TrialShell(ROOT / "tests/reference/python/try-bash")
        shells["rust"] = TrialShell(ROOT / "try-bash")
        samples = {backend: [] for backend in shells}
        for iteration in range(10):
            order = ("python", "rust") if iteration % 2 == 0 else ("rust", "python")
            for backend in order:
                samples[backend].append(shells[backend].measure())
        result = {"method": "10 alternating paired runs per backend in actual trial launchers with the user's Bash hooks. Time from submitting omarchy theme lsit to displaying confirmation. Every correction cancelled, history disabled; includes original failing Omarchy command.",
                  "samples_ms": samples, "summary": {}}
        for backend, values in samples.items():
            result["summary"][backend] = {"median_ms": statistics.median(values),
                                           "min_ms": min(values), "max_ms": max(values)}
        report_path = ROOT / "benchmarks/comparison-results.json"
        report = json.loads(report_path.read_text())
        report["terminal"] = result
        report_path.write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps(result["summary"], indent=2))
    finally:
        for shell in shells.values():
            shell.close()


if __name__ == "__main__":
    main()
