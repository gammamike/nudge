"""Batch regression cases preserve arguments and refuse unreviewed operations."""
import json
import os
import pty
import select
import shlex
import signal
import time
import unittest

from support import ROOT
import test_cli_profiles as profiles
import test_cli_adapters as adapters

CASES = json.loads((ROOT / 'tests/fixtures/expansion-cases.json').read_text())


class ExpansionTests(unittest.TestCase):
    def setUp(self):
        profiles.ProfileTests.setUp(self)
        fixtures = json.loads(self.fixture_path.read_text())
        nested = json.loads((ROOT / 'tests/fixtures/nested-cli-help.json').read_text())
        fixtures.update(nested)
        self.fixture_path.write_text(json.dumps(fixtures))
        for name in nested:
            tool = self.path / name
            tool.write_text(adapters.TOOL)
            tool.chmod(0o755)

    suggest = profiles.ProfileTests.suggest

    def test_each_batch_positive_negative_and_valid_runtime_failure(self):
        for name, case in CASES.items():
            for positive in case['positive']:
                with self.subTest(batch=case['batch'], tool=name, command=positive['input']):
                    result = self.suggest(positive['input'])
                    self.assertEqual(result['argv'], positive['argv'], result)
                    self.assertIsNone(self.suggest(shlex.join(positive['argv']), ai=True)['suggestion'])
                    self.assertIsNone(self.suggest(positive['input'], ADAPTER_METADATA_FAILURE='1', NUDGE_CACHE_DIR=str(self.path / 'missing-cache' / name))['suggestion'])
            for command in case['negative']:
                with self.subTest(batch=case['batch'], tool=name, command=command):
                    self.assertIsNone(self.suggest(command, ai=True)['suggestion'])
        self.assertFalse((self.path / 'executed').exists())
        self.assertFalse((self.path / 'ai-prompt').exists())

    def test_kubectl_plugin_names_are_never_rewritten_or_executed(self):
        plugin = self.path / 'kubectl-gte'
        plugin.write_text('#!/bin/sh\nprintf "plugin executed\\n" >> "$ADAPTER_EXECUTED"\nexit 99\n')
        plugin.chmod(0o755)
        self.assertIsNone(self.suggest('kubectl gte pods', ai=True)['suggestion'])
        self.assertFalse((self.path / 'ai-prompt').exists())
        self.assertFalse((self.path / 'executed').exists())
        calls = [json.loads(line) for line in (self.path / 'calls').read_text().splitlines()]
        self.assertTrue(all(name == 'kubectl' for name, _ in calls))

    def test_kubectl_requires_separate_global_option_evidence(self):
        data = json.loads(self.fixture_path.read_text())
        data['kubectl']['["options"]']['stdout'] = ''
        self.fixture_path.write_text(json.dumps(data))
        self.assertIsNone(self.suggest('kubectl gte pods -n private-namespace', ai=True)['suggestion'])
        self.assertFalse((self.path / 'ai-prompt').exists())

    def test_each_batch_bash_cancel_and_accept_preserves_arguments(self):
        representatives = {}
        for case in CASES.values():
            representatives.setdefault(case['batch'], case['positive'][0])
        for batch, positive in representatives.items():
            with self.subTest(batch=batch):
                marker = self.path / 'executed'
                marker.unlink(missing_ok=True)
                expected = positive['argv'][1:]
                rc = self.path / 'bashrc'
                rc.write_text(f'HISTFILE=/dev/null\nHISTCONTROL=ignoreboth\nPS1="__READY__ "\nsource "{ROOT}/nudge.bash"\n')
                pid, fd = pty.fork()
                if pid == 0:
                    env = dict(self.env, NUDGE_LOCAL_ONLY='1', TERM='dumb', ADAPTER_EXPECT=json.dumps(expected))
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
                    found, pending = pending[:end], pending[end:]
                    return found
                try:
                    until(b'__READY__ ')
                    for key in (b'x', b'\n'):
                        os.write(fd, positive['input'].encode() + b'\n')
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
                            self.assertEqual(json.loads(marker.read_text()), [positive['argv'][0], expected])
                finally:
                    os.kill(pid, signal.SIGKILL)
                    os.waitpid(pid, 0)
                    os.close(fd)
