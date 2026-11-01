"""Provider boundary and Bash confirmation tests, with no live model requests."""
import json
import os
from pathlib import Path
import signal
import subprocess
import tempfile
import time
import unittest

from test_parity import BINARY, original


FAKE_CLAUDE = '''#!/usr/bin/env python3
import json, os, subprocess, sys, time
from pathlib import Path
args = sys.argv[1:]
capture = Path(os.environ['FAKE_CAPTURE'])
record = {'args':args, 'cwd':os.getcwd(), 'overrides':[
    k for k in os.environ if k.startswith(('ANTHROPIC_', 'CLAUDE_'))],
    'config_dir':os.environ.get('CLAUDE_CONFIG_DIR')}
if args[-3:] == ['auth', 'status', '--json']:
    capture.with_suffix('.auth').write_text(json.dumps(record))
    print(os.environ.get('FAKE_AUTH', '{"loggedIn":true,"authMethod":"claude.ai","apiProvider":"firstParty"}'))
    sys.exit(0)
record['prompt'] = sys.stdin.read()
capture.write_text(json.dumps(record))
if 'FAKE_SLEEP' in os.environ:
    child = subprocess.Popen(['/bin/sleep', '60'])
    Path(os.environ['FAKE_CHILD']).write_text(str(child.pid))
    time.sleep(60)
data = json.loads(record['prompt'].split('\\n', 1)[1])
index = next(x['id'] for x in data['candidates'] if x['command'] == 'herdr server stop')
selection = json.loads(os.environ.get('FAKE_SELECTION', json.dumps({'candidate_id':index})))
print(os.environ.get('FAKE_RESPONSE', json.dumps({'type':'result', 'subtype':'success', 'is_error':False, 'structured_output':selection})))
sys.exit(int(os.environ.get('FAKE_EXIT', '0')))
'''


class ClaudeTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name)
        self.env = {k: v for k, v in os.environ.items() if not k.startswith('NUDGE_')}
        self.env.update(PATH=f"{self.path}:{os.environ['PATH']}", NUDGE_PROVIDER='claude',
                        NUDGE_CONFIG=str(self.path / 'config.json'),
                        NUDGE_CACHE_DIR=str(self.path / 'cache'),
                        FAKE_CAPTURE=str(self.path / 'capture'), FAKE_CHILD=str(self.path / 'child'),
                        ANTHROPIC_API_KEY='sentinel', ANTHROPIC_AUTH_TOKEN='sentinel',
                        ANTHROPIC_BASE_URL='sentinel', CLAUDE_CODE_USE_BEDROCK='1',
                        CLAUDE_CODE_OAUTH_TOKEN='sentinel', CLAUDE_CODE_SIMPLE='1',
                        CLAUDE_CONFIG_DIR=str(self.path / 'account'))
        self.write_executable('claude', FAKE_CLAUDE)
        self.write_executable('herdr', '''#!/bin/bash
if [[ $* == --help ]]; then
  printf 'Common commands:\\n  herdr server stop                Stop the server\\n'
elif [[ $* == 'server --help' ]]; then
  printf 'Commands:\\n  stop                    Stop the server\\n'
else
  exit 2
fi
''')
        self.write_executable('omarchy', '#!/bin/bash\nprintf \'{"commands": []}\\n\'\n')
        self.write_executable('codex', '#!/bin/bash\nexit 91\n')

    def write_executable(self, name, source):
        path = self.path / name
        path.write_text(source)
        path.chmod(0o755)

    def run_nudge(self, line='herdr halt', *args, **updates):
        result = subprocess.run([str(BINARY), 'suggest', '--command', line, *args],
                                env=dict(self.env, **updates), capture_output=True, text=True, timeout=8)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def capture(self):
        return json.loads(Path(self.env['FAKE_CAPTURE']).read_text())

    def test_selection_auth_and_isolation(self):
        result = self.run_nudge()
        self.assertEqual(result['suggestion'], 'herdr server stop')
        self.assertEqual(result['source'], 'claude')
        captured = self.capture()
        auth = json.loads(Path(self.env['FAKE_CAPTURE'] + '.auth').read_text())
        for record in (captured, auth):
            self.assertEqual(set(record['overrides']),
                             {'CLAUDE_CONFIG_DIR', 'CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC'})
            self.assertEqual(record['config_dir'], self.env['CLAUDE_CONFIG_DIR'])
            self.assertIn('--safe-mode', record['args'])
            self.assertEqual(record['args'][record['args'].index('--setting-sources') + 1], '')
            settings = json.loads(record['args'][record['args'].index('--settings') + 1])
            self.assertTrue(settings['disableAllHooks'])
            self.assertEqual(settings['forceLoginMethod'], 'claudeai')
        args = captured['args']
        self.assertEqual(args[args.index('--model') + 1], 'haiku')
        self.assertEqual(args[args.index('--tools') + 1], '')
        self.assertEqual(json.loads(args[args.index('--mcp-config') + 1]), {'mcpServers': {}})
        for flag in ('--strict-mcp-config', '--disable-slash-commands', '--no-chrome',
                     '--no-session-persistence', '--permission-prompts'):
            self.assertIn(flag, args)
        data = json.loads(captured['prompt'].split('\n', 1)[1])
        self.assertEqual(set(data), {'failed_command', 'candidates'})
        self.assertLessEqual(len(data['candidates']), 24)
        self.assertFalse(Path(captured['cwd']).exists(), 'temporary prompt directory leaked')

    def test_refuses_non_subscription_auth(self):
        for method in ('api_key', 'api_key_helper', 'third_party', 'oauth_token', 'none'):
            auth = json.dumps({'loggedIn': True, 'authMethod': method, 'apiProvider': 'firstParty'})
            self.assertIsNone(self.run_nudge(FAKE_AUTH=auth)['suggestion'])
            self.assertFalse(Path(self.env['FAKE_CAPTURE']).exists())
        for auth in ('{}', 'not json', '{"loggedIn":false}',
                     '{"loggedIn":true,"authMethod":"claude.ai","apiProvider":"bedrock"}'):
            self.assertIsNone(self.run_nudge(FAKE_AUTH=auth)['suggestion'])

    def test_rejects_invalid_selection_and_error_envelopes(self):
        for selection in ({'candidate_id': -1}, {'candidate_id': 999}, {'candidate_id': True},
                          {'candidate_id': '0'}, {'candidate_id': .5}, {}, None,
                          {'candidate_id': 0, 'command': 'arbitrary command'}):
            self.assertIsNone(self.run_nudge(FAKE_SELECTION=json.dumps(selection))['suggestion'])
        for response in ('not json', '{"candidate_id":0}',
                         '{"type":"result","subtype":"success","is_error":true,"structured_output":{"candidate_id":0}}',
                         '{"type":"result","subtype":"error_max_turns","is_error":false,"structured_output":{"candidate_id":0}}'):
            self.assertIsNone(self.run_nudge(FAKE_RESPONSE=response)['suggestion'])
        self.assertIsNone(self.run_nudge(FAKE_EXIT='1')['suggestion'])

    def test_local_and_out_of_scope_never_call_provider(self):
        self.assertEqual(self.run_nudge('herdr stop')['source'], 'local')
        for line in ('hrdr stop', 'herd stop', 'herdr server stop', 'herdr halt | cat',
                     'herdr halt; id', 'herdr --help'):
            self.assertIsNone(self.run_nudge(line)['suggestion'])
        self.assertIsNone(self.run_nudge('herdr halt', '--local-only')['suggestion'])
        self.assertIsNone(self.run_nudge(NUDGE_LOCAL_ONLY='1')['suggestion'])
        self.assertFalse(Path(self.env['FAKE_CAPTURE'] + '.auth').exists())

    def test_model_settings_and_provider_validation(self):
        self.assertEqual(self.run_nudge('herdr halt', '--provider', 'claude',
                                       NUDGE_PROVIDER='codex')['source'], 'claude')
        self.run_nudge(NUDGE_MODEL='codex-legacy-model', NUDGE_CODEX_MODEL='codex-only')
        args = self.capture()['args']
        self.assertEqual(args[args.index('--model') + 1], 'haiku')
        self.run_nudge(NUDGE_CLAUDE_MODEL='custom-claude-model')
        args = self.capture()['args']
        self.assertEqual(args[args.index('--model') + 1], 'custom-claude-model')
        self.run_nudge('herdr halt', '--model', 'cli-selected-model', NUDGE_CLAUDE_MODEL='environment-model')
        args = self.capture()['args']
        self.assertEqual(args[args.index('--model') + 1], 'cli-selected-model')
        for args in (['--provider', 'invalid'], ['--force-codex']):
            result = subprocess.run([str(BINARY), 'suggest', '--command', 'herdr halt', *args],
                                    env=self.env, capture_output=True)
            self.assertNotEqual(result.returncode, 0)

    def test_missing_cli_declines_without_switching_provider(self):
        (self.path / 'claude').unlink()
        result = self.run_nudge(PATH=str(self.path))
        self.assertIsNone(result['suggestion'])
        self.assertEqual(result['source'], 'claude')
        self.assertIn('authentication check failed', result['reason'])

    def child_stopped(self):
        pid = int(Path(self.env['FAKE_CHILD']).read_text())
        deadline = time.monotonic() + 1
        while time.monotonic() < deadline:
            path = Path(f'/proc/{pid}/stat')
            if not path.exists() or path.read_text().split()[2] == 'Z':
                return
            time.sleep(.01)
        self.fail('Claude descendant survived cancellation')

    def test_timeout_kills_descendant(self):
        result = self.run_nudge(FAKE_SLEEP='1', NUDGE_AI_TIMEOUT='0.2')
        self.assertIsNone(result['suggestion'])
        self.assertIn('Claude timed out', result['reason'])
        self.child_stopped()

    def test_interrupt_kills_descendant(self):
        process = subprocess.Popen([str(BINARY), 'suggest', '--command', 'herdr halt'],
                                   env=dict(self.env, FAKE_SLEEP='1'),
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            deadline = time.monotonic() + 3
            while not Path(self.env['FAKE_CHILD']).exists():
                self.assertLess(time.monotonic(), deadline, 'mock Claude did not start')
                time.sleep(.01)
            process.send_signal(signal.SIGINT)
            process.communicate(timeout=2)
            self.assertEqual(process.returncode, 130)
            self.child_stopped()
        finally:
            if process.poll() is None:
                process.kill()
                process.communicate()

    def test_bash_confirmation_executes_only_after_enter(self):
        shell = original.Shell()
        self.addCleanup(shell.close)
        claude = shell.path / 'claude'
        claude.write_text(FAKE_CLAUDE)
        claude.chmod(0o755)
        shell.command(f'export NUDGE_LOCAL_ONLY=0 NUDGE_PROVIDER=claude FAKE_CAPTURE="{self.path}/tty-capture"')
        shell.send(b'herdr halt\n')
        output = shell.until(b'Any other key to cancel ')
        self.assertIn(b'checking with Claude', output)
        self.assertIn(b'nudge [claude,', output)
        self.assertFalse(shell.marker.exists())
        shell.send(b'x')
        shell.until(b'__READY__ ')
        self.assertFalse(shell.marker.exists())
        shell.command(':')
        shell.send(b'herdr halt\n')
        shell.until(b'Any other key to cancel ')
        shell.send(b'\n')
        self.assertIn(b'FAKE_SERVER_STOPPED', shell.until(b'__READY__ '))
        self.assertEqual(shell.marker.read_text(), 'server stop\n')


if __name__ == '__main__':
    unittest.main()
