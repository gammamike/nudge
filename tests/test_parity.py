"""Cross-language parity and the original PTY contract; no live model calls."""
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
PYTHON = ROOT / "tests/reference/python"
BINARY = ROOT / "target/release/nudge-rust"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


original = load("original_tests", PYTHON / "tests/test_nudge.py")
python = original.nudge
original.ROOT = ROOT


class RustShellTests(original.ShellTests):
    """Run the identical seven Bash/TTY tests against the Rust binary."""


class ParityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory()
        cls.path = Path(cls.directory.name)
        cls.env = {k: v for k, v in os.environ.items() if not k.startswith("NUDGE_")}
        cls.env.update(NUDGE_CACHE_DIR=str(cls.path / "cache"), NUDGE_PROVIDER="codex")
        cls.env["NUDGE_CONFIG"] = str(cls.path / "config.json")
        # Use the captured catalog on every host; no installed Herdr or Omarchy
        # and no files outside this checkout are needed for parity tests.
        fixture = ROOT / "tests/fixtures/legacy-help.json"
        for name in ("herdr", "omarchy"):
            executable = cls.path / name
            executable.write_text('''#!/usr/bin/env python3
import json,sys
from pathlib import Path
data=json.loads(Path(''' + repr(str(fixture)) + ''').read_text())
key=json.dumps(sys.argv[1:],separators=(',',':'))
row=data[Path(sys.argv[0]).name].get(key)
if row is None:
    sys.exit(2)
print(row['stdout'],end='')
print(row['stderr'],end='',file=sys.stderr)
sys.exit(row['status'])
''')
            executable.chmod(0o755)
        cls.env["PATH"] = f"{cls.path}:{os.environ['PATH']}"
        subprocess.run([sys.executable, str(PYTHON / "nudge.py"), "refresh"],
                       env=cls.env, check=True, capture_output=True)
        cls.data = json.loads((cls.path / "cache/catalog.json").read_text())

    @classmethod
    def tearDownClass(cls):
        cls.directory.cleanup()

    def rust(self, line, *args, env=None):
        result = subprocess.run([str(BINARY), "suggest", "--command", line, *args],
                                env=env or self.env, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        value = json.loads(result.stdout)
        value.pop("elapsed_ms")
        return value

    def test_same_discovered_catalog(self):
        subprocess.run([str(BINARY), "refresh"], env=self.env, check=True, capture_output=True)
        rust = json.loads((self.path / "cache/catalog.json").read_text())
        for key in ("binaries", "entries", "version"):
            self.assertEqual(rust[key], self.data[key], key)

    def test_generated_local_cases_match_python(self):
        cases = {"herdr stop", "herdr halt", "omarchy reload terminal", "omarchy nightlight",
                 "herdr stop; id", "herdr $(id)", "herdr stop | cat", "herdr stop\n",
                 "herdr\tstop", "herdr stop ", " herdr stop", "herdr  stop", "herdr --help",
                 "sudo herdr stop", "omarchy theme set nord", "omarchy theme sett nord", ""}
        for entry in self.data["entries"]:
            route = entry["argv"]
            cases.add(" ".join(route))
            for i in range(1, len(route)):
                cases.add(" ".join(route[:i] + route[i + 1:]))
                if len(route[i]) >= 3:
                    word = route[i]
                    changed = word[:-2] + word[-1] + word[-2]
                    cases.add(" ".join(route[:i] + [changed] + route[i + 1:]))
        with patch.object(python, "catalog", return_value=self.data):
            for line in sorted(cases):
                expected = python.suggest(line, local_only=True)
                expected.pop("elapsed_ms")
                self.assertEqual(self.rust(line, "--local-only"), expected, line)
        print(f"\nMatched {len(cases)} generated/local cases across both implementations.")

    def fake_codex(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name)
        executable = path / "codex"
        executable.write_text('''#!/usr/bin/env python3
import json,os,sys,time,subprocess
from pathlib import Path
if sys.argv[1:] == ['login','status']:
    print('Logged in using '+os.environ.get('FAKE_AUTH','ChatGPT'))
else:
    prompt=sys.stdin.read()
    Path(os.environ['FAKE_CAPTURE']).write_text(json.dumps({'prompt':prompt,'args':sys.argv[1:],'api_present':any(k in os.environ for k in ('OPENAI_API_KEY','CODEX_API_KEY'))}))
    if 'FAKE_SLEEP' in os.environ:
        child=subprocess.Popen(['/bin/sleep','60'])
        Path(os.environ['FAKE_CHILD']).write_text(str(child.pid))
        time.sleep(60)
    Path(sys.argv[sys.argv.index('-o')+1]).write_text(json.dumps({'candidate_id':json.loads(os.environ.get('FAKE_ID','0'))}))
''')
        executable.chmod(0o755)
        return dict(self.env, PATH=f"{path}:{os.environ['PATH']}", FAKE_CAPTURE=str(path / "capture"),
                    FAKE_CHILD=str(path / "child"), OPENAI_API_KEY="sentinel", CODEX_API_KEY="sentinel")

    def test_identical_codex_prompts_and_flags(self):
        env = self.fake_codex()
        for line in ("herdr halt", "omarchy reload terminal", "omarchy list themes",
                     "omarchy darken screen", "herdr reload"):
            subprocess.run([sys.executable, str(PYTHON / "nudge.py"), "suggest", "--command", line,
                            "--force-codex"], env=env, check=True, capture_output=True)
            expected = json.loads(Path(env["FAKE_CAPTURE"]).read_text())
            self.rust(line, "--force-codex", env=env)
            actual = json.loads(Path(env["FAKE_CAPTURE"]).read_text())
            self.assertEqual(actual["prompt"], expected["prompt"], line)
            self.assertFalse(actual["api_present"])
            for data in (actual, expected):
                for flag in ("-C", "--output-schema", "-o"):
                    data["args"][data["args"].index(flag) + 1] = "TEMP"
            self.assertEqual(actual["args"], expected["args"])

    def test_api_auth_and_bad_model_output_decline(self):
        env = self.fake_codex()
        api = self.rust("herdr halt", env=dict(env, FAKE_AUTH="an API key"))
        self.assertIsNone(api["suggestion"])
        self.assertIn("API billing is disabled", api["reason"])
        for picked in ("999", "-1", "true", '"0"', "0.5"):
            result = self.rust("herdr halt", env=dict(env, FAKE_ID=picked))
            self.assertIsNone(result["suggestion"], picked)

    def child_stopped(self, env):
        pid = int(Path(env["FAKE_CHILD"]).read_text())
        deadline = time.monotonic() + 1
        while time.monotonic() < deadline:
            path = Path(f"/proc/{pid}/stat")
            if not path.exists() or path.read_text().split()[2] == "Z":
                return
            time.sleep(.01)
        self.fail("child process survived cleanup")

    def test_timeout_kills_descendant(self):
        env = dict(self.fake_codex(), FAKE_SLEEP="1", NUDGE_CODEX_TIMEOUT="0.2")
        result = self.rust("herdr halt", env=env)
        self.assertIsNone(result["suggestion"])
        self.assertIn("timed out", result["reason"])
        self.child_stopped(env)

    def test_interrupt_kills_descendant(self):
        env = dict(self.fake_codex(), FAKE_SLEEP="1")
        process = subprocess.Popen([str(BINARY), "suggest", "--command", "herdr halt"],
                                   env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            deadline = time.monotonic() + 3
            while not Path(env["FAKE_CHILD"]).exists():
                if time.monotonic() > deadline:
                    self.fail("mock Codex did not start")
                time.sleep(.01)
            process.send_signal(signal.SIGINT)
            process.communicate(timeout=2)
            self.assertEqual(process.returncode, 130)
            self.child_stopped(env)
        finally:
            if process.poll() is None:
                process.kill()
                process.communicate()


if __name__ == "__main__":
    unittest.main(verbosity=2)
