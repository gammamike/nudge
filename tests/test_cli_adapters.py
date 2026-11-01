"""Linux CLI grammar/argument preservation with installed-help fixtures."""
import json
import os
from pathlib import Path
import pty
import select
import shlex
import signal
import subprocess
import tempfile
import time
import unittest

from test_parity import BINARY, ROOT

FIXTURES = Path(__file__).parent / 'fixtures/linux-cli-help.json'

TOOL = '''#!/usr/bin/env python3
import json,os,sys
from pathlib import Path
name=Path(sys.argv[0]).name
args=sys.argv[1:]
with open(os.environ['ADAPTER_CALLS'],'a') as f: f.write(json.dumps([name,args])+'\\n')
if os.environ.get('ADAPTER_METADATA_FAILURE') == '1':
    sys.exit(1)
query=args[:]
if name == 'git':
    while query and query[0] in ('-C','--git-dir','--work-tree'):
        query=query[2:]
    while query and query[0] in ('--no-pager','--paginate','--literal-pathspecs'):
        query=query[1:]
data=json.loads(Path(os.environ['ADAPTER_FIXTURES']).read_text())[name]
key=json.dumps(query,separators=(',',':'))
if key in data:
    row=data[key]
    if query == ['compose','version','--short']:
        print(os.environ.get('ADAPTER_COMPOSE_VERSION','5.6.1'))
    else:
        print(row['stdout'],end='')
        print(row['stderr'],end='',file=sys.stderr)
        if name=='git' and query==['--list-cmds=main,others,alias']:
            print(os.environ.get('ADAPTER_GIT_ALIASES',''))
    sys.exit(row['status'])
if args == json.loads(os.environ.get('ADAPTER_EXPECT','null')):
    with open(os.environ['ADAPTER_EXECUTED'],'a') as f: f.write(json.dumps([name,args])+'\\n')
    print('ACCEPTED_TEST_COMMAND')
    sys.exit(7)
print('unknown or failed test command',file=sys.stderr)
sys.exit(2)
'''

CODEX = '''#!/usr/bin/env python3
import json,os,sys
from pathlib import Path
if sys.argv[1:] == ['login','status']:
    print('Logged in using ChatGPT')
else:
    prompt=sys.stdin.read()
    Path(os.environ['ADAPTER_AI_PROMPT']).write_text(prompt)
    data=json.loads(prompt.split('\\n',1)[1])
    chosen=next((c['id'] for c in data['candidates'] if c['command']==os.environ.get('ADAPTER_AI_CHOICE','git status')),-1)
    Path(sys.argv[sys.argv.index('-o')+1]).write_text(json.dumps({'candidate_id':chosen}))
'''


class AdapterTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name)
        for name in ('git', 'docker', 'systemctl', 'journalctl'):
            script = self.path / name
            script.write_text(TOOL)
            script.chmod(0o755)
        script = self.path / 'codex'
        script.write_text(CODEX)
        script.chmod(0o755)
        self.env = {k: v for k, v in os.environ.items() if not k.startswith('NUDGE_')}
        self.env.update(PATH=f"{self.path}:{os.environ['PATH']}",
                        NUDGE_CACHE_DIR=str(self.path / 'cache'), NUDGE_CONFIG=str(self.path / 'config.json'),
                        NUDGE_PROVIDER='codex', ADAPTER_FIXTURES=str(FIXTURES),
                        ADAPTER_CALLS=str(self.path / 'calls'),
                        ADAPTER_EXECUTED=str(self.path / 'executed'),
                        ADAPTER_AI_PROMPT=str(self.path / 'ai-prompt'), HISTFILE='/dev/null')

    def suggest(self, line, ai=False, status=1, **updates):
        args = [str(BINARY), 'suggest', '--command', line, '--status', str(status)]
        if not ai:
            args.append('--local-only')
        result = subprocess.run(args, env=dict(self.env, **updates), text=True,
                                capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((self.path / 'executed').exists())
        return json.loads(result.stdout)

    def test_command_and_flag_corrections(self):
        pairs = [
            ('git statsu', ['git', 'status']),
            ('git chekout feature/topic', ['git', 'checkout', 'feature/topic']),
            ("git -C '/tmp/repo with spaces' statsu --short", ['git', '-C', '/tmp/repo with spaces', 'status', '--short']),
            ('git status --shrot', ['git', 'status', '--short']),
            ('git logs --oneline -5', ['git', 'log', '--oneline', '-5']),
            ('git diff --name-onyl --cached', ['git', 'diff', '--name-only', '--cached']),
            ('docker contianer ls --all', ['docker', 'container', 'ls', '--all']),
            ('docker logs --tial=10 api', ['docker', 'logs', '--tail=10', 'api']),
            ('docker --context dev logs --tial 10 api', ['docker', '--context', 'dev', 'logs', '--tail', '10', 'api']),
            ('docker comopse ps', ['docker', 'compose', 'ps']),
            ("docker compose -f 'compose dev.yml' -p app restat api", ['docker', 'compose', '-f', 'compose dev.yml', '-p', 'app', 'restart', 'api']),
            ('docker compose logs --tial 10 api', ['docker', 'compose', 'logs', '--tail', '10', 'api']),
            ('systemctl --user restat example.service', ['systemctl', '--user', 'restart', 'example.service']),
            ('systemctl statsu example.service --no-pager', ['systemctl', 'status', 'example.service', '--no-pager']),
            ('systemctl --user list-timres --all', ['systemctl', '--user', 'list-timers', '--all']),
            ('systemctl --lines 10 statsu example.service', ['systemctl', '--lines', '10', 'status', 'example.service']),
            ('journalctl --uint=example.service -n 20 --no-pager', ['journalctl', '--unit=example.service', '-n', '20', '--no-pager']),
            ("journalctl --sinec '1 hour ago' --user", ['journalctl', '--since', '1 hour ago', '--user']),
        ]
        for line, expected in pairs:
            with self.subTest(line=line):
                value = self.suggest(line)
                self.assertEqual(value['argv'], expected, value)
                self.assertEqual(shlex.split(value['suggestion']), expected)
                self.assertEqual(value['source'], 'local')

    def test_literal_values_and_command_payloads_preserved(self):
        pairs = [
            ("git ad 'a b' ''", None),  # Short command typos remain ambiguous.
            ("git add -- 'statsu' '--shrot'", None),
            ("git status --shrot -- 'a b' '' '$(touch nope)' 'a'\\''b'", ['git', 'status', '--short', '--', 'a b', '', '$(touch nope)', "a'b"]),
            ("git commti -m '--shrot is a message' -- 'a b'", ['git', 'commit', '-m', '--shrot is a message', '--', 'a b']),
            ("docker run --detahc alpine sh -c 'printf hello'", ['docker', 'run', '--detach', 'alpine', 'sh', '-c', 'printf hello']),
            ("docker exec --interacitve api sh -c 'printf hello'", ['docker', 'exec', '--interactive', 'api', 'sh', '-c', 'printf hello']),
            ("journalctl --uint api.service --grep '--no-pagr' _COMM=worker", ['journalctl', '--unit', 'api.service', '--grep', '--no-pagr', '_COMM=worker']),
        ]
        for line, expected in pairs:
            with self.subTest(line=line):
                value = self.suggest(line)
                self.assertEqual(value.get('argv'), expected, value)

    def test_valid_runtime_failures_and_aliases_are_untouched(self):
        for line in ['git status', 'git checkout missing-branch', 'git status --sho',
                     'docker logs missing-container', 'docker compose -f missing.yml up -d',
                     'systemctl --user status missing.service', 'systemctl --no-pag status missing.service',
                     'journalctl --unit missing.service', 'journalctl --since nonsense',
                     'git st', 'git co', 'git external-helper']:
            with self.subTest(line=line):
                value = self.suggest(line, ai=True, ADAPTER_GIT_ALIASES='external-helper')
                self.assertIsNone(value['suggestion'])
        self.assertFalse((self.path / 'ai-prompt').exists())
        self.assertIsNone(self.suggest('git statsu', ai=True, ADAPTER_GIT_ALIASES='statsu')['suggestion'])
        self.assertFalse((self.path / 'ai-prompt').exists())

    def test_risky_or_compound_forms_decline(self):
        for line in ['git rset --hard', 'git cleen', 'git chekout -qf main',
                     'git chekout --forc main', 'git chekout -- file.txt',
                     'git brnach -d old', 'git push --froce', 'git -c alias.foo=status statsu',
                     'docker system pruen', 'docker compose dwon', 'docker rmi image',
                     'systemctl rebot', 'systemctl enbale --now example.service',
                     'journalctl --vacum-time=1d', 'journalctl --rotat',
                     'git statsu; id', 'git statsu | cat', 'git add $(id)',
                     'git chekout \"$BRANCH\"', 'git add *.rs', 'sudo systemctl statsu api',
                     'gti status', 'git statsu --shrot', 'docker --config custom comopse ps',
                     'docker stpo', 'systemctl restat']:
            with self.subTest(line=line):
                self.assertIsNone(self.suggest(line, ai=True)['suggestion'])
        self.assertFalse((self.path / 'executed').exists())

    def test_ai_selects_syntax_only_then_revalidates(self):
        value = self.suggest("git statuzzz --short 'private path'", ai=True)
        self.assertEqual(value['argv'], ['git', 'status', '--short', 'private path'])
        prompt = (self.path / 'ai-prompt').read_text()
        self.assertNotIn('private path', prompt)
        self.assertNotIn('--short', prompt)
        self.assertEqual(json.loads(prompt.split('\n', 1)[1])['failed_command'], 'git statuzzz')
        self.assertIsNone(self.suggest("git statuzzz --unknown-option 'private path'", ai=True)['suggestion'])

    def test_success_interrupt_and_metadata_failure_decline(self):
        for status in (0, 130):
            self.assertIsNone(self.suggest('git statsu', status=status)['suggestion'])
        self.assertFalse((self.path / 'calls').exists())
        result = self.suggest('git statsu', ADAPTER_METADATA_FAILURE='1')
        self.assertIsNone(result['suggestion'])
        self.assertIn('metadata unavailable', result['reason'])

    def test_help_cache_and_executable_invalidation(self):
        self.suggest('docker logs --tial 10 api')
        calls = lambda: [json.loads(line) for line in (self.path / 'calls').read_text().splitlines()]
        before = len(calls())
        self.suggest('docker logs --tial 10 api')
        self.assertEqual(len(calls()), before)
        executable = self.path / 'docker'
        executable.write_text(executable.read_text() + '\n# changed version\n')
        self.suggest('docker logs --tial 10 api')
        self.assertGreater(len(calls()), before)

    def test_compose_plugin_version_invalidates_help(self):
        self.suggest('docker compose restat api')
        calls = lambda: [json.loads(line) for line in (self.path / 'calls').read_text().splitlines()]
        count = lambda: sum(args == ['compose', 'restart', '--help'] for _, args in calls())
        self.assertEqual(count(), 1)
        self.suggest('docker compose restat api', ADAPTER_COMPOSE_VERSION='next-test-version')
        self.assertEqual(count(), 2)

    def test_bash_all_roots_cancel_and_confirm_exact_arguments(self):
        for line, expected in [
            ("git statsu --short -- 'a b'", ['status', '--short', '--', 'a b']),
            ('docker logs --tial 2 api', ['logs', '--tail', '2', 'api']),
            ("docker compose -f 'compose dev.yml' restat api", ['compose', '-f', 'compose dev.yml', 'restart', 'api']),
            ('systemctl --user statsu api.service', ['--user', 'status', 'api.service']),
            ('journalctl --uint api.service -n 2', ['--unit', 'api.service', '-n', '2']),
        ]:
            with self.subTest(line=line):
                marker = self.path / 'executed'
                marker.unlink(missing_ok=True)
                rc = self.path / 'bashrc'
                rc.write_text(f'HISTFILE=/dev/null\nHISTCONTROL=ignoreboth\nPS1="__READY__ "\nsource "{ROOT}/nudge.bash"\n')
                pid, fd = pty.fork()
                if pid == 0:
                    env = dict(self.env, NUDGE_LOCAL_ONLY='1', TERM='dumb', ADAPTER_EXPECT=json.dumps(expected))
                    os.execve('/bin/bash', ['bash', '--noprofile', '--rcfile', str(rc), '-i'], env)
                pending = b''
                def until(text):
                    nonlocal pending
                    deadline = time.monotonic() + 8
                    while text not in pending:
                        self.assertLess(time.monotonic(), deadline, pending[-1000:])
                        if select.select([fd], [], [], .05)[0]:
                            pending += os.read(fd, 65536)
                    end = pending.index(text) + len(text)
                    result, pending = pending[:end], pending[end:]
                    return result
                try:
                    until(b'__READY__ ')
                    os.write(fd, line.encode() + b'\n')
                    until(b'Any other key to cancel ')
                    self.assertFalse(marker.exists())
                    os.write(fd, b'x')
                    until(b'__READY__ ')
                    self.assertFalse(marker.exists())
                    os.write(fd, b':\n')
                    until(b'__READY__ ')
                    os.write(fd, line.encode() + b'\n')
                    until(b'Any other key to cancel ')
                    os.write(fd, b'\n')
                    self.assertIn(b'ACCEPTED_TEST_COMMAND', until(b'__READY__ '))
                    rows = marker.read_text().splitlines()
                    self.assertEqual(len(rows), 1)
                    self.assertEqual(json.loads(rows[0])[1], expected)
                finally:
                    os.kill(pid, signal.SIGKILL)
                    os.waitpid(pid, 0)
                    os.close(fd)
