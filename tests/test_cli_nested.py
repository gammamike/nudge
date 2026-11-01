"""Nested Linux grammars using captured help and harmless executable doubles."""
import json
import os
from pathlib import Path
import pty
import select
import shlex
import signal
import subprocess
import time
import unittest

import test_cli_adapters as adapters
from test_parity import BINARY, ROOT

FIXTURES = Path(__file__).parent / 'fixtures/nested-cli-help.json'
PAIRS = [
 ('nix biuld nixpkgs#hello', 'nix build nixpkgs#hello'),
 ('nix --extra-experimental-features "nix-command flakes" flake shwo .', 'nix --extra-experimental-features "nix-command flakes" flake show .'),
 ('nix build --argstr name "private value" --no-lnik .#app', 'nix build --argstr name "private value" --no-link .#app'),
 ('nix build --override-input nixpkgs github:NixOS/nixpkgs --dry-rnu .', 'nix build --override-input nixpkgs github:NixOS/nixpkgs --dry-run .'),
 ('nix profile lsit --json', 'nix profile list --json'),
 ('nix store diff-clousres /nix/store/old /nix/store/new', 'nix store diff-closures /nix/store/old /nix/store/new'),
 ('nix develop --commnad bash -c "echo literal"', 'nix develop --command bash -c "echo literal"'),
 ('nix shlel nixpkgs#hello -c hello --not-a-nix-flag', 'nix shell nixpkgs#hello -c hello --not-a-nix-flag'),
 ('nix env shlel nixpkgs#hello', 'nix env shell nixpkgs#hello'),
 ('nix rnu .#app -- --not-a-nix-flag', 'nix run .#app -- --not-a-nix-flag'),
 ('iwctl statoin wlan0 show', 'iwctl station wlan0 show'),
 ('iwctl station lsit', 'iwctl station list'),
 ('iwctl device wlan0 shwo', 'iwctl device wlan0 show'),
 ('iwctl adapter phy0 shwo', 'iwctl adapter phy0 show'),
 ('iwctl known-networks "Home WiFi" shwo', 'iwctl known-networks "Home WiFi" show'),
 ('iwctl --passphrase "private password" station wlan0 conenct "Home WiFi"', 'iwctl --passphrase "private password" station wlan0 connect "Home WiFi"'),
 ('iwctl station wlan0 get-netwroks rssi-dbms', 'iwctl station wlan0 get-networks rssi-dbms'),
 ('iwctl station wlan0 disconenct', 'iwctl station wlan0 disconnect'),
 ('zellij list-sessoins --short', 'zellij list-sessions --short'),
 ('zellij --session "my session" action list-paens --json', 'zellij --session "my session" action list-panes --json'),
 ('zellij ac move-foucs left', 'zellij ac move-focus left'),
 ('zellij atatch --create "my session"', 'zellij attach --create "my session"'),
 ('zellij run --floatign --name "my pane" -- echo --not-a-zellij-flag', 'zellij run --floating --name "my pane" -- echo --not-a-zellij-flag'),
 ('zellij action rename-pnae "my pane"', 'zellij action rename-pane "my pane"'),
 ('zellij setup --dump-conifg', 'zellij setup --dump-config'),
 ('strace --follow-froks -s128 -e trace=openat --output="trace file" echo --not-a-strace-flag', 'strace --follow-forks -s128 -e trace=openat --output="trace file" echo --not-a-strace-flag'),
 ('strace --string-limt=128 --attach=123', 'strace --string-limit=128 --attach=123'),
 ('strace -ff -tt -yy --sumamry -- echo hello', 'strace -ff -tt -yy --summary -- echo hello'),
 ('strace --stack-trcae=symbol echo hello', 'strace --stack-trace=symbol echo hello'),
]

class NestedTests(unittest.TestCase):
    suggest = adapters.AdapterTests.suggest

    def setUp(self):
        adapters.AdapterTests.setUp(self)
        self.fixture_path = self.path / 'fixture.json'
        self.fixture_path.write_text(FIXTURES.read_text())
        self.env['ADAPTER_FIXTURES'] = str(self.fixture_path)
        for name in ('nix', 'iwctl', 'zellij', 'strace'):
            script = self.path / name
            script.write_text(adapters.TOOL)
            script.chmod(0o755)

    def test_corrections_and_unchanged_literal_arguments(self):
        for original, corrected in PAIRS:
            with self.subTest(original=original):
                result = self.suggest(original)
                self.assertEqual(result.get('argv'), shlex.split(corrected), result)
                self.assertEqual(self.suggest(corrected)['suggestion'], None)
        calls = [json.loads(line) for line in (self.path/'calls').read_text().splitlines()]
        fixtures = json.loads(FIXTURES.read_text())
        for name, args in calls:
            self.assertIn(json.dumps(args,separators=(',',':')), fixtures[name])

    def test_opaque_payloads_selectors_excluded_commands_and_invalid_forms(self):
        cases = [
            'nix build missing#package', 'nix build --argstr name',
            'nix biuld --argstr name', 'nix biuld --repair .',
            'nix store delet /nix/store/path', 'nix profile remvoe hello',
            'nix show-config', 'nix develop . -c echo --no-lnik',
            'nix run . -- --no-lnik', 'nix biuld # comment',
            'nix build --not-a-real-flag .', 'nix build --argstr=name value --no-lnik',
            'iwctl station typo-device show', 'iwctl station wlan0 connect "typo SSID"',
            'iwctl station secret-device', 'iwctl station wlan0 connect',
            'iwctl station wlan0 conenct', 'iwctl station wlan0 shwo extra',
            'iwctl station list shwo', 'iwctl device wlan0 set-proprety Powered off',
            'iwctl known-networks Home foregt', 'iwctl station wlan0 shwo --dont-ask',
            'zellij kill-sessoin important', 'zellij action close-pnae',
            'zellij action wirte-chars "private data"',
            'zellij run --floatign echo hello', 'zellij run --floatign --',
            'zellij action move-foucs', 'zellij atatch --force-run-commands old',
            'zellij run -- echo --floatign', 'zellij action rename-pane "misspelled name"',
            'strace echo --follow-froks', 'strace --follow-fork echo',
            'strace --follow-froks', 'strace --follow-froks -p not-a-pid',
            'strace --follow-froks --inject=openat:error=ENOENT echo',
            'strace --follow-froks -e fault=openat echo',
            'strace --follow-froks -e inject=openat echo',
            'strace --follow-froks -o "|execute-me" echo',
            'strace --follow-froks --user=root echo',
            'strace --follow-froks --kill-on-exit echo',
            'strace --string-limt=bad echo',
            'strace --follow-froks -p123 ""',
        ]
        for line in cases:
            with self.subTest(line=line):
                self.assertIsNone(self.suggest(line)['suggestion'])

    def test_model_receives_only_command_syntax_and_must_pass_revalidation(self):
        for line, choice, private in [
            ('nix flake explain-secret .#private --override-input private-input private-url', 'nix flake metadata', ['.#private','private-input','private-url']),
            ('iwctl --passphrase private-password station private-device join-network private-ssid', 'iwctl station connect', ['private-password','private-device','private-ssid']),
            ('zellij --session private-session action change-name private-title', 'zellij action rename-pane', ['private-session','private-title']),
        ]:
            with self.subTest(line=line):
                result = self.suggest(line,ai=True,ADAPTER_AI_CHOICE=choice)
                self.assertIsNotNone(result['argv'],result)
                prompt = (self.path/'ai-prompt').read_text()
                for value in private:self.assertNotIn(value,prompt)
        result=self.suggest('iwctl station wlan0 join-network',ai=True,ADAPTER_AI_CHOICE='iwctl station connect')
        self.assertIsNone(result['suggestion'])

    def test_values_and_options_never_trigger_model_requests(self):
        for line in ['iwctl station private-device', 'iwctl station wlan0 connect private-ssid', 'strace --nonsense echo', 'zellij run -- echo --floatign', 'nix develop -c echo --nonsense']:
            self.assertIsNone(self.suggest(line,ai=True)['suggestion'])
        self.assertFalse((self.path/'ai-prompt').exists())

    def test_missing_metadata_and_changed_nix_schema_decline(self):
        for line in ['nix biuld .', 'iwctl station wlan0 shwo', 'zellij list-sessoins', 'strace --follow-froks echo']:
            self.assertIsNone(self.suggest(line,ai=True,ADAPTER_METADATA_FAILURE='1')['suggestion'])
        data=json.loads(FIXTURES.read_text())
        data['nix']['["__dump-cli"]']['stdout']='{"args":{"unexpected":true}}'
        self.fixture_path.write_text(json.dumps(data))
        self.assertIsNone(self.suggest('nix biuld .',ai=True)['suggestion'])
        self.assertFalse((self.path/'ai-prompt').exists())

    def test_nix_option_arity_is_checked_against_installed_metadata(self):
        data=json.loads(FIXTURES.read_text())
        dump=json.loads(data['nix']['["__dump-cli"]']['stdout'])
        dump['args']['commands']['build']['flags']['argstr']['arity']=1
        del dump['args']['commands']['flake']['commands']['show']
        data['nix']['["__dump-cli"]']['stdout']=json.dumps(dump)
        self.fixture_path.write_text(json.dumps(data))
        self.assertIsNone(self.suggest('nix biuld --argstr name value .')['suggestion'])
        self.assertIsNone(self.suggest('nix flake shwo .')['suggestion'])

    def test_nix_shell_at_root_or_under_env_uses_the_advertised_route(self):
        data=json.loads(FIXTURES.read_text())
        dump=json.loads(data['nix']['["__dump-cli"]']['stdout'])
        commands=dump['args']['commands']
        commands['shell']=commands.pop('env')['commands']['shell']
        data['nix']['["__dump-cli"]']['stdout']=json.dumps(dump)
        self.fixture_path.write_text(json.dumps(data))
        result=self.suggest('nix shlel nixpkgs#hello -c hello')
        self.assertEqual(result.get('argv'), ['nix','shell','nixpkgs#hello','-c','hello'], result)

    def test_help_cache_avoids_repeated_processes_and_invalidates_on_executable_change(self):
        self.assertIsNotNone(self.suggest('iwctl station wlan0 shwo')['suggestion'])
        first=(self.path/'calls').read_text()
        self.assertIsNotNone(self.suggest('iwctl station wlan0 shwo')['suggestion'])
        self.assertEqual((self.path/'calls').read_text(),first)
        script=self.path/'iwctl';script.write_text(script.read_text()+'\n# changed executable\n')
        self.assertIsNotNone(self.suggest('iwctl station wlan0 shwo')['suggestion'])
        self.assertGreater(len((self.path/'calls').read_text()),len(first))

    def test_bash_cancel_and_accept_exact_argv(self):
        for line, expected in [
            ('nix biuld nixpkgs#hello', ['build','nixpkgs#hello']),
            ('iwctl station wlan0 conenct "Home WiFi"', ['station','wlan0','connect','Home WiFi']),
            ('zellij run --floatign -- echo "a b"', ['run','--floating','--','echo','a b']),
            ('strace --follow-froks echo "a b"', ['--follow-forks','echo','a b']),
        ]:
            with self.subTest(line=line):
                marker = self.path / 'executed'
                marker.unlink(missing_ok=True)
                rc = self.path / 'bashrc'
                rc.write_text(f'HISTFILE=/dev/null\nHISTCONTROL=ignoreboth\nPS1="__READY__ "\nsource "{ROOT}/nudge.bash"\n')
                pid, fd = pty.fork()
                if pid == 0:
                    env = dict(self.env, NUDGE_LOCAL_ONLY='1', TERM='dumb', ADAPTER_EXPECT=json.dumps(expected))
                    os.execve('/bin/bash', ['bash','--noprofile','--rcfile',str(rc),'-i'], env)
                pending = b''
                def until(text):
                    nonlocal pending
                    deadline = time.monotonic() + 8
                    while text not in pending:
                        self.assertLess(time.monotonic(), deadline, pending[-1000:])
                        if select.select([fd],[],[],.05)[0]:
                            pending += os.read(fd,65536)
                    end = pending.index(text) + len(text)
                    found,pending = pending[:end],pending[end:]
                    return found
                try:
                    until(b'__READY__ ')
                    os.write(fd,line.encode()+b'\n')
                    until(b'Any other key to cancel ')
                    self.assertFalse(marker.exists())
                    os.write(fd,b'x')
                    until(b'__READY__ ')
                    self.assertFalse(marker.exists())
                    os.write(fd,b':\n')
                    until(b'__READY__ ')
                    os.write(fd,line.encode()+b'\n')
                    until(b'Any other key to cancel ')
                    os.write(fd,b'\n')
                    self.assertIn(b'ACCEPTED_TEST_COMMAND',until(b'__READY__ '))
                    self.assertEqual(json.loads(marker.read_text())[1],expected)
                finally:
                    os.kill(pid,signal.SIGKILL)
                    os.waitpid(pid,0)
                    os.close(fd)
