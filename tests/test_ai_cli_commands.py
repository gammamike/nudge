"""AI CLI command syntax is corrected locally; prompts never become requests."""
import json
import os
import pty
import select
import shlex
import signal
import subprocess
import time
import unittest

from support import BINARY, ROOT
import test_cli_profiles as profiles
import test_cli_adapters as adapters

CASES = {
    'gemini': [('gemini --verison', ['gemini', '--version']),
               ('gemini mcp lsit', ['gemini', 'mcp', 'list']),
               ('gemini extensions lsit --output-format=json', ['gemini', 'extensions', 'list', '--output-format=json']),
               ('gemini --list-sesions', ['gemini', '--list-sessions'])],
    'codex': [('codex mcp --hlep', ['codex','mcp','--help']),
              ('codex --verison', ['codex', '--version']),
              ('codex login statua', ['codex', 'login', 'status']),
              ('codex mcp lsit --json', ['codex', 'mcp', 'list', '--json']),
              ('codex mcp get "private server" --jsno', ['codex', 'mcp', 'get', 'private server', '--json'])],
    'ollama': [('ollama --verison', ['ollama', '--version']),
               ('ollama lsit', ['ollama', 'list']),
               ('ollama show qwen3:0.6b --paramters', ['ollama', 'show', 'qwen3:0.6b', '--parameters'])],
    'claude': [('claude auth --hlep', ['claude','auth','--help']),
               ('claude --verison', ['claude', '--version']),
               ('claude auth statua --text', ['claude', 'auth', 'status', '--text']),
               ('claude mcp lsit', ['claude', 'mcp', 'list'])],
}


class AiCliTests(unittest.TestCase):
    def setUp(self):
        profiles.ProfileTests.setUp(self)
        fixtures = json.loads(self.fixture_path.read_text())
        captured = json.loads((ROOT / 'tests/fixtures/nested-cli-help.json').read_text())
        for name in CASES:
            fixtures[name] = captured[name]
            executable = self.path / name
            executable.write_text(adapters.TOOL)
            executable.chmod(0o755)
        self.fixture_path.write_text(json.dumps(fixtures))

    suggest = profiles.ProfileTests.suggest

    def check_tool(self, name):
        for command, expected in CASES[name]:
            with self.subTest(command=command):
                result = self.suggest(command)
                self.assertEqual(result['argv'], expected, result)
                self.assertEqual(result['source'], 'local')
                self.assertIsNone(self.suggest(shlex.join(expected), ai=True)['suggestion'])
                self.assertIsNone(self.suggest(command, ADAPTER_METADATA_FAILURE='1',
                                              NUDGE_CACHE_DIR=str(self.path / 'missing' / name))['suggestion'])
        self.assertFalse((self.path / 'ai-prompt').exists())
        self.assertFalse((self.path / 'executed').exists())
        calls = [json.loads(line) for line in (self.path / 'calls').read_text().splitlines()]
        self.assertTrue(all(args[-1:] == ['--help'] for _, args in calls), calls)

    def test_gemini(self):
        self.check_tool('gemini')

    def test_codex(self):
        self.check_tool('codex')

    def test_ollama(self):
        self.check_tool('ollama')

    def test_claude(self):
        self.check_tool('claude')

    def test_prompts_inference_authentication_mutations_and_unknown_flags_decline(self):
        for command in (
            'gemini "mcp lsit"', 'gemini --prompt "extensions lsit"',
            'gemini --yolo --verison', 'gemini extensions instal private-source',
            'gemini mcp add private-name private-command', 'gemini mcp enable private-name',
            'codex "mcp lsit"', 'codex logni status', 'codex --modle private-model "private prompt"',
            'codex exec --jsno "private prompt"', 'codex login --device-auth',
            'codex mcp add server --url https://private.example', 'codex mcp rm private-server',
            'claude "auth statua"', 'claude --print "mcp lsit"',
            'claude auth logni', 'claude mcp remove private-server',
            'claude --dangerously-skip-permissions --verison',
            'ollama rn model', 'ollama pull model', 'ollama rm model',
            'ollama show --paramters', 'ollama show --parameters --unknown model',
            'ollama show --modelfile -- -paramters',
        ):
            with self.subTest(command=command):
                self.assertIsNone(self.suggest(command, ai=True)['suggestion'])
        self.assertFalse((self.path / 'ai-prompt').exists())
        self.assertFalse((self.path / 'executed').exists())

    def test_missing_leaf_option_evidence_declines(self):
        fixture = json.loads(self.fixture_path.read_text())
        fixture['ollama']['["show","--help"]']['stdout'] = fixture['ollama']['["show","--help"]']['stdout'].replace('--parameters', '--unreviewed')
        self.fixture_path.write_text(json.dumps(fixture))
        self.assertIsNone(self.suggest('ollama show private-model --paramters', ai=True)['suggestion'])
        self.assertFalse((self.path / 'ai-prompt').exists())

    def test_force_ai_never_sends_ai_cli_commands_to_a_provider(self):
        for rows in CASES.values():
            result = subprocess.run([str(BINARY), 'suggest', '--command', rows[0][0], '--force-ai'],
                                    env=self.env, check=True, capture_output=True, text=True)
            self.assertIsNone(json.loads(result.stdout)['suggestion'])
        calls = [json.loads(line) for line in (self.path / 'calls').read_text().splitlines()]
        self.assertTrue(all(args[-1:] == ['--help'] for _, args in calls), calls)

    def test_advertised_but_unreviewed_commands_and_aliases_are_preserved(self):
        self.assertIsNone(self.suggest('ollama ls', ai=True)['suggestion'])
        fixture = json.loads(self.fixture_path.read_text())
        fixture['ollama']['["--help"]']['stdout'] += '\n  lsit         Installed extension or future command\n'
        self.fixture_path.write_text(json.dumps(fixture))
        self.assertIsNone(self.suggest('ollama lsit', ai=True, NUDGE_CACHE_DIR=str(self.path / 'fresh-help'))['suggestion'])
        self.assertFalse((self.path / 'ai-prompt').exists())

    def test_each_tool_bash_confirmation_and_argument_preservation(self):
        for name, cases in CASES.items():
            command, expected = cases[-1]
            with self.subTest(name=name):
                marker = self.path / 'executed'
                marker.unlink(missing_ok=True)
                rc = self.path / 'bashrc'
                rc.write_text(f'HISTFILE=/dev/null\nPS1="__READY__ "\nsource "{ROOT}/nudge.bash"\n')
                pid, fd = pty.fork()
                if pid == 0:
                    env = dict(self.env, NUDGE_LOCAL_ONLY='1', TERM='dumb', ADAPTER_EXPECT=json.dumps(expected[1:]))
                    os.execve('/bin/bash', ['bash', '--noprofile', '--rcfile', str(rc), '-i'], env)
                pending = b''
                def until(needle):
                    nonlocal pending
                    deadline = time.monotonic() + 8
                    while needle not in pending:
                        self.assertLess(time.monotonic(), deadline, pending[-1000:])
                        if select.select([fd], [], [], .05)[0]:
                            pending += os.read(fd, 65536)
                    end = pending.index(needle) + len(needle)
                    output, pending = pending[:end], pending[end:]
                    return output
                try:
                    until(b'__READY__ ')
                    for key in (b'x', b'\n'):
                        os.write(fd, command.encode() + b'\n')
                        until(b'Any other key to cancel ')
                        self.assertFalse(marker.exists())
                        os.write(fd, key)
                        output = until(b'__READY__ ')
                        if key == b'x':
                            self.assertFalse(marker.exists())
                            os.write(fd, b':\n')
                            until(b'__READY__ ')
                        else:
                            self.assertIn(b'ACCEPTED_TEST_COMMAND', output)
                            self.assertEqual(json.loads(marker.read_text()), [name, expected[1:]])
                finally:
                    os.kill(pid, signal.SIGKILL)
                    os.waitpid(pid, 0)
                    os.close(fd)
