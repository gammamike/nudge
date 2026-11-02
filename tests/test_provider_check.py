"""Provider readiness and fallback messages using mock CLIs and HTTP transport."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from support import BINARY, ROOT


FAKE = '''#!/usr/bin/python3
import json, os, sys
from pathlib import Path
name = Path(sys.argv[0]).name
args = sys.argv[1:]
if args == ['login', 'status']:
    print('Logged in using ' + os.environ.get('FAKE_AUTH', 'ChatGPT'))
    sys.exit(0)
if args[-3:] == ['auth', 'status', '--json']:
    print(json.dumps({'loggedIn':True, 'authMethod':os.environ.get('FAKE_AUTH', 'claude.ai'), 'apiProvider':'firstParty'}))
    sys.exit(0)
if name == 'curl' and args[args.index('--url') + 1].endswith('/api/show'):
    print('{"model_info":{}}')
    sys.exit(0)
prompt = sys.stdin.read()
if name == 'curl':
    prompt = json.loads(prompt)['messages'][1]['content']
Path(os.environ['FAKE_CAPTURE']).write_text(prompt)
if os.environ.get('FAKE_EXIT'):
    sys.exit(int(os.environ['FAKE_EXIT']))
if os.environ.get('FAKE_SLEEP'):
    import time
    time.sleep(2)
selection = json.loads(os.environ.get('FAKE_SELECTION', '{"candidate_id":0}'))
if name == 'codex':
    Path(args[args.index('-o') + 1]).write_text(json.dumps(selection))
elif name == 'claude':
    print(json.dumps({'type':'result', 'subtype':'success', 'is_error':False, 'structured_output':selection}))
else:
    message = {'role':'assistant', 'content':json.dumps(selection)}
    print(json.dumps({'done':True, 'done_reason':'stop', 'message':message,
                     'choices':[{'finish_reason':'stop','message':message}]}))
'''


class ProviderCheckTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.home = Path(self.directory.name)
        self.config = self.home / 'config.json'
        self.capture = self.home / 'request'
        self.env = dict(HOME=str(self.home), PATH=str(self.home) + ':/usr/bin',
                        NUDGE_CONFIG=str(self.config), NUDGE_CACHE_DIR=str(self.home / 'cache'),
                        FAKE_CAPTURE=str(self.capture))
        for name in ('codex', 'claude', 'curl'):
            path = self.home / name
            path.write_text(FAKE)
            path.chmod(0o700)
        for name, content in (
            ('herdr', '#!/bin/bash\nprintf "  herdr server stop                Stop the server\\n"\n'),
            ('omarchy', '#!/bin/bash\nprintf \'{"commands":[]}\\n\'\n'),
        ):
            path = self.home / name
            path.write_text(content)
            path.chmod(0o700)

    def run_cli(self, provider, *args, **overrides):
        result = subprocess.run([str(BINARY), *args, '--provider', provider, '--model', 'test-model'],
                                env=dict(self.env, **overrides), text=True, capture_output=True, timeout=8)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_each_provider_checks_model_without_saving_or_discovery(self):
        for provider in ('codex', 'claude', 'ollama', 'local'):
            with self.subTest(provider=provider):
                result = self.run_cli(provider, 'check-provider', NUDGE_LOCAL_ONLY='1')
                self.assertTrue(result['ok'], result)
                self.assertEqual(result['provider'], provider)
                self.assertEqual(result['model'], 'test-model')
                data = json.loads(self.capture.read_text().split('\n', 1)[1])
                self.assertEqual(data['failed_command'], 'nudge-probe chekc')
                self.assertEqual([c['command'] for c in data['candidates']], ['nudge-probe check'])
                self.assertFalse(self.config.exists())
                self.assertFalse((self.home / 'cache/catalog.json').exists())

    def test_abstention_and_invalid_responses_have_distinct_messages(self):
        for provider in ('codex', 'claude', 'ollama', 'local'):
            for action in (['check-provider'], ['suggest', '--command', 'herdr halt']):
                for selection, expected in (
                    ({'candidate_id': -1}, 'no suitable correction found'),
                    ({'candidate_id': 99999}, 'invalid response'),
                    ({'candidate_id': -2}, 'invalid response'),
                    ({'candidate_id': -1, 'command': 'anything'}, 'invalid response'),
                    ({'candidate_id': '0'}, 'invalid response'),
                ):
                    with self.subTest(provider=provider, action=action, selection=selection):
                        result = self.run_cli(provider, *action, FAKE_SELECTION=json.dumps(selection))
                        self.assertIn(expected, result.get('message', result.get('reason')))
                        self.assertFalse(result.get('ok', False))
                        self.assertIsNone(result.get('suggestion'))

    def test_non_subscription_login_does_not_send_request(self):
        for provider in ('codex', 'claude'):
            result = self.run_cli(provider, 'check-provider', FAKE_AUTH='api-key')
            self.assertFalse(result['ok'])
            self.assertIn('login', result['message'])
            self.assertFalse(self.capture.exists())

    def test_missing_cli_is_not_connected(self):
        for provider in ('codex', 'claude'):
            path = self.home / provider
            path.write_text('#!/bin/bash\nexit 127\n')
            result = self.run_cli(provider, 'check-provider')
            self.assertFalse(result['ok'])
        self.assertFalse(self.capture.exists())

    def test_request_failure_and_timeout_are_not_connected(self):
        for provider in ('codex', 'claude', 'ollama', 'local'):
            result = self.run_cli(provider, 'check-provider', FAKE_EXIT='1')
            self.assertFalse(result['ok'])
            result = self.run_cli(provider, 'check-provider', FAKE_SLEEP='1', NUDGE_AI_TIMEOUT='0.1')
            self.assertFalse(result['ok'])
            self.assertIn('timed out', result['message'])

    def test_bridge_tests_unsaved_choices_and_preserves_settings(self):
        self.config.write_text('{"provider":"codex","models":{"codex":"saved-model"}}')
        before = self.config.read_bytes()
        (self.home / 'nudge-bash').symlink_to(BINARY)
        result = subprocess.run(['/bin/bash', str(ROOT / 'companion/omarchy/bridge.sh'),
                                 'test', 'claude', 'test-model', ''], env=self.env,
                                text=True, capture_output=True, timeout=8)
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertTrue(data['ok'])
        self.assertEqual(data['provider'], 'claude')
        self.assertEqual(data['model'], 'test-model')
        self.assertEqual(self.config.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
