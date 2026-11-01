"""Catalog regression and subscription-provider boundary tests for Rust."""
import json
import os
from pathlib import Path
import signal
import subprocess
import tempfile
import time
import unittest

from support import ROOT, BINARY


class CatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory()
        cls.path = Path(cls.directory.name)
        cls.env = {k: v for k, v in os.environ.items() if not k.startswith("NUDGE_")}
        cls.env.update(NUDGE_CACHE_DIR=str(cls.path / "cache"), NUDGE_PROVIDER="codex")
        cls.env["NUDGE_CONFIG"] = str(cls.path / "config.json")
        # All catalog discovery uses captured help through temporary executables.
        fixture = ROOT / "tests/fixtures/catalog-help.json"
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
        subprocess.run([str(BINARY), "refresh"],
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

    def test_discovered_catalog_matches_reviewed_entries(self):
        expected = json.loads((ROOT / 'tests/fixtures/catalog-entries.json').read_text())
        self.assertEqual(self.data['entries'], expected)
        for name in ('herdr', 'omarchy'):
            self.assertEqual(self.data['binaries'][name][0], str(self.path / name))

    def test_catalog_correction_regressions(self):
        cases = json.loads((ROOT / 'tests/fixtures/catalog-cases.json').read_text())
        self.assertEqual(len(cases), 1823)
        for expected in cases:
            with self.subTest(command=expected['command']):
                actual = self.rust(expected['command'], '--local-only')
                executable = actual.pop('executable', None)
                if expected['suggestion'] is not None:
                    self.assertEqual(executable, str(self.path / expected['argv'][0]))
                else:
                    self.assertIsNone(executable)
                self.assertEqual(actual, expected)

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
        return dict(self.env, PATH=f"{path}:{self.env['PATH']}", FAKE_CAPTURE=str(path / "capture"),
                    FAKE_CHILD=str(path / "child"), OPENAI_API_KEY="sentinel", CODEX_API_KEY="sentinel")

    def test_subscription_selection_uses_constrained_prompt_and_isolated_flags(self):
        env = self.fake_codex()
        for line in ('herdr halt', 'omarchy reload terminal', 'omarchy list themes'):
            result = self.rust(line, '--force-ai', env=env)
            actual = json.loads(Path(env['FAKE_CAPTURE']).read_text())
            data = json.loads(actual['prompt'].split('\n', 1)[1])
            self.assertEqual(data['failed_command'], line)
            self.assertEqual([c['id'] for c in data['candidates']], list(range(len(data['candidates']))))
            self.assertIn(result['suggestion'], [c['command'] for c in data['candidates']])
            self.assertFalse(actual['api_present'])
            args = actual['args']
            for flag in ('--no-daemon', '--ignore-user-config', '--ephemeral', '--skip-git-repo-check'):
                self.assertIn(flag, args)
            self.assertEqual(args[args.index('--sandbox') + 1], 'read-only')
            for setting in ('approval_policy="never"', 'web_search="disabled"', 'forced_login_method="chatgpt"'):
                self.assertIn(setting, args)
            for feature in ('shell_tool', 'apps', 'plugins', 'hooks', 'multi_agent', 'browser_use', 'computer_use', 'image_generation'):
                self.assertIn(['--disable', feature], [args[i:i+2] for i in range(len(args)-1)])
            self.assertFalse(Path(args[args.index('-C') + 1]).exists())

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
