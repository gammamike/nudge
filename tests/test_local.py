"""Exercise real loopback HTTP against test servers, never an actual model."""
import http.server
import json
import os
from pathlib import Path
import signal
import subprocess
import tempfile
import threading
import time
import unittest

from support import BINARY, Shell


class LocalTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name)
        self.env = {k: v for k, v in os.environ.items() if not k.startswith('NUDGE_')}
        self.env.update(NUDGE_CONFIG=str(self.path / 'config.json'),
                        NUDGE_CACHE_DIR=str(self.path / 'cache'),
                        PATH=f"{self.path}:{os.environ['PATH']}")
        for name, text in {
            'herdr': "#!/bin/bash\nprintf 'Common commands:\\n  herdr server stop                Stop the server\\n'\n",
            'omarchy': "#!/bin/bash\nprintf '{\"commands\": []}\\n'\n",
            'claude': f"#!/bin/bash\ntouch '{self.path}/hosted-called'\nexit 85\n",
            'codex': f"#!/bin/bash\ntouch '{self.path}/hosted-called'\nexit 85\n",
        }.items():
            script = self.path / name
            script.write_text(text)
            script.chmod(0o755)
        self.requests = []
        self.response = None
        self.remote = False
        self.delay = 0
        self.http_status = 200
        owner = self

        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass

            def do_GET(self):
                self.respond(None)

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                self.respond(body)

            def respond(self, body):
                owner.requests.append((self.path, body, dict(self.headers)))
                if self.path == '/api/show':
                    result = {'model_info': {}}
                    if owner.remote:
                        result['remote_host'] = 'https://cloud.example'
                elif self.path == '/api/tags':
                    result = {'models': [{'name': 'tiny:q4'}, {'name': 'cloud', 'remote_host': 'https://cloud.example'}]}
                elif self.path == '/v1/models':
                    result = {'data': [{'id': 'tiny:q4'}, {'id': 'bigger:q8'}]}
                else:
                    time.sleep(owner.delay)
                    data = json.loads(body['messages'][1]['content'].split('\n', 1)[1])
                    chosen = next(c['id'] for c in data['candidates'] if c['command'] == 'herdr server stop')
                    message = {'role': 'assistant', 'content': json.dumps({'candidate_id': chosen})}
                    result = ({'done': True, 'done_reason': 'stop', 'message': message}
                              if self.path == '/api/chat' else
                              {'choices': [{'finish_reason': 'stop', 'message': message}]})
                    if owner.response is not None:
                        result = owner.response
                raw = (result if isinstance(result, str) else json.dumps(result)).encode()
                self.send_response(owner.http_status)
                if owner.http_status == 302:
                    self.send_header('Location', 'https://cloud.example/should-never-follow')
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(raw)))
                self.end_headers()
                try:
                    self.wfile.write(raw)
                except (BrokenPipeError, ConnectionResetError):
                    pass

        self.server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.server.daemon_threads = False
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.close_server)
        self.base = f'http://127.0.0.1:{self.server.server_port}'

    def close_server(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.assertFalse((self.path / 'hosted-called').exists(), 'unexpected hosted-provider fallback')

    def run_cli(self, *args, updates=None, ok=True):
        result = subprocess.run([str(BINARY), *args], env=dict(self.env, **(updates or {})),
                                capture_output=True, text=True, timeout=5)
        if ok:
            self.assertEqual(result.returncode, 0, result.stderr)
            return json.loads(result.stdout)
        self.assertNotEqual(result.returncode, 0)
        return result

    def suggest(self, provider='ollama', **kwargs):
        return self.run_cli('suggest', '--provider', provider, '--model', 'tiny:q4',
                            '--endpoint', self.base + ('/v1' if provider == 'local' else ''),
                            '--command', 'herdr halt', **kwargs)

    def test_both_protocols_select_from_catalog(self):
        for provider in ('ollama', 'local'):
            result = self.suggest(provider)
            self.assertEqual(result['suggestion'], 'herdr server stop')
            self.assertEqual(result['source'], 'ollama' if provider == 'ollama' else 'local-llm')
            route, body, headers = self.requests[-1]
            self.assertFalse(body['stream'])
            self.assertNotIn('tools', body)
            self.assertNotIn('Authorization', headers)
            self.assertEqual(body['model'], 'tiny:q4')
            schema = body.get('format', body.get('response_format', {}).get('json_schema', {}).get('schema'))
            self.assertFalse(schema['additionalProperties'])
        self.assertEqual([r[0] for r in self.requests], ['/api/show', '/api/chat', '/v1/chat/completions'])

    def test_local_discovery(self):
        for provider, route, expected in (
            ('ollama', '', ['tiny:q4']), ('local', '/v1', ['bigger:q8', 'tiny:q4'])
        ):
            result = self.run_cli('models', '--provider', provider, '--endpoint', self.base + route)
            self.assertEqual(result['models'], expected)
        self.run_cli('models', '--provider', 'claude', ok=False)

    def test_remote_ollama_declines_before_sending_command(self):
        self.remote = True
        result = self.suggest()
        self.assertIsNone(result['suggestion'])
        self.assertIn('cloud/remote', result['reason'])
        self.assertEqual([r[0] for r in self.requests], ['/api/show'])
        self.assertEqual(set(self.requests[0][1]), {'model'})

    def test_bad_responses_decline(self):
        for payload in ('not json', {'error': 'bad'}, {'choices': []},
                        {'choices': [{'finish_reason': 'length', 'message': {'role': 'assistant', 'content': '{"candidate_id":0}'}}]},
                        {'choices': [{'finish_reason': 'stop', 'message': {'role': 'assistant', 'content': '{"candidate_id":0}', 'tool_calls': [{}]}}]}):
            self.response = payload
            self.assertIsNone(self.suggest('local')['suggestion'])
        for selection in ({'candidate_id': True}, {'candidate_id': -1}, {'candidate_id': 999},
                          {'candidate_id': '0'}, {'candidate_id': 0, 'command': 'bad'}):
            self.response = {'choices': [{'finish_reason': 'stop', 'message':
                             {'role': 'assistant', 'content': json.dumps(selection)}}]}
            self.assertIsNone(self.suggest('local')['suggestion'])

    def test_http_failure_and_redirect_never_fall_back(self):
        for code in (500, 302):
            self.http_status = code
            self.response = {}
            self.assertIsNone(self.suggest('local')['suggestion'])
        self.assertEqual(len(self.requests), 2)

    def test_proxy_and_curl_config_ignored(self):
        (self.path / '.curlrc').write_text('header = "Authorization: sentinel"\nproxy = "http://127.0.0.1:1"\n')
        result = self.suggest('local', updates={'CURL_HOME': str(self.path),
                             'http_proxy': 'http://127.0.0.1:1', 'ALL_PROXY': 'http://127.0.0.1:1',
                             'OPENAI_API_KEY': 'sentinel', 'ANTHROPIC_API_KEY': 'sentinel'})
        self.assertEqual(result['suggestion'], 'herdr server stop')
        self.assertNotIn('Authorization', self.requests[-1][2])

    def test_timeout_and_interrupt(self):
        self.delay = 1
        result = self.suggest('local', updates={'NUDGE_AI_TIMEOUT': '.1'})
        self.assertIsNone(result['suggestion'])
        self.requests.clear()
        process = subprocess.Popen([str(BINARY), 'suggest', '--provider', 'local', '--model', 'tiny:q4',
                                    '--endpoint', self.base + '/v1', '--command', 'herdr halt'],
                                   env=self.env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            deadline = time.monotonic() + 2
            while not self.requests:
                self.assertLess(time.monotonic(), deadline)
                time.sleep(.01)
            process.send_signal(signal.SIGINT)
            process.communicate(timeout=1)
            self.assertEqual(process.returncode, 130)
        finally:
            if process.poll() is None:
                process.kill()
                process.communicate()

    def test_no_model_or_rules_only_need_no_server(self):
        result = self.run_cli('suggest', '--provider', 'ollama', '--command', 'herdr halt')
        self.assertIsNone(result['suggestion'])
        self.assertIn('choose an installed model', result['reason'])
        result = self.run_cli('suggest', '--provider', 'ollama', '--command', 'herdr stop')
        self.assertEqual(result['source'], 'local')
        self.suggest(updates={'NUDGE_LOCAL_ONLY': '1'})
        self.assertEqual(self.requests, [])

    def test_configuration_persists_per_provider_and_precedence(self):
        self.run_cli('config', '--provider', 'claude', '--model', 'sonnet')
        self.run_cli('config', '--provider', 'ollama', '--model', 'tiny:q4', '--endpoint', self.base)
        result = self.run_cli('config')
        self.assertEqual(result['provider'], 'ollama')
        self.assertEqual(result['model'], 'tiny:q4')
        self.assertEqual(result['config']['models']['claude'], 'sonnet')
        self.assertEqual((self.path / 'config.json').stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.run_cli('suggest', '--command', 'herdr halt')['source'], 'ollama')
        result = self.run_cli('config', updates={'NUDGE_PROVIDER': 'claude', 'NUDGE_CLAUDE_MODEL': 'custom-version'})
        self.assertEqual(result['model'], 'custom-version')
        result = self.run_cli('config', '--provider', 'ollama', '--model', 'override',
                              updates={'NUDGE_PROVIDER': 'claude'})
        self.assertEqual(result['config']['models']['ollama'], 'override')
        self.assertEqual(self.run_cli('config')['model'], 'override')

    def test_invalid_configuration_and_endpoints(self):
        for endpoint in ('http://example.com:1234', 'http://10.0.0.1:1234', 'http://127.0.0.1:1234/?a=b'):
            self.run_cli('config', '--provider', 'local', '--endpoint', endpoint, ok=False)
        self.assertFalse((self.path / 'config.json').exists())
        self.run_cli('config', '--provider', 'claude', '--model', 'bad\nname', ok=False)
        (self.path / 'config.json').write_text('{"unknown_field": true}')
        self.run_cli('config', ok=False)
        self.assertEqual(self.requests, [])

    def test_local_confirmation_requires_enter(self):
        # forkpty must run before the HTTP serving thread is active.
        self.server.shutdown()
        self.thread.join()
        shell = Shell()
        self.addCleanup(shell.close)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        shell.command(f'export NUDGE_LOCAL_ONLY=0 NUDGE_PROVIDER=local NUDGE_LOCAL_MODEL=tiny:q4 NUDGE_LOCAL_URL="{self.base}/v1"')
        shell.send(b'herdr halt\n')
        output = shell.until(b'Any other key to cancel ')
        self.assertIn(b'nudge [local-llm,', output)
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
