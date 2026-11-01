"""Reviewed Linux profiles against captured installed help; no real workloads."""
import json
import os
from pathlib import Path
import pty
import select
import shlex
import signal
import time
import unittest
import subprocess

from test_parity import BINARY, ROOT
import test_cli_adapters as adapters

PROFILES = json.loads((ROOT / 'data/linux-profiles.json').read_text())
FIXTURES = json.loads((ROOT / 'tests/fixtures/linux-profile-help.json').read_text())
CASES = json.loads((ROOT / 'tests/fixtures/linux-profile-cases.json').read_text())


class ProfileTests(unittest.TestCase):
    suggest = adapters.AdapterTests.suggest

    def setUp(self):
        adapters.AdapterTests.setUp(self)
        combined = json.loads(Path(self.env['ADAPTER_FIXTURES']).read_text())
        combined.update(FIXTURES)
        self.fixture_path = self.path / 'fixtures.json'
        self.fixture_path.write_text(json.dumps(combined))
        self.env['ADAPTER_FIXTURES'] = str(self.fixture_path)
        for name in PROFILES:
            script = self.path / name
            script.write_text(adapters.TOOL)
            script.chmod(0o755)

    def test_each_active_profile_has_a_real_help_fixture_and_positive_case(self):
        self.assertEqual(set(PROFILES), set(CASES))
        self.assertEqual(set(PROFILES), set(FIXTURES))
        for name, case in CASES.items():
            with self.subTest(tool=name):
                self.assertFalse(FIXTURES[name].get('missing'))
                value = self.suggest(case['input'])
                self.assertEqual(value['argv'], case['argv'], value)
                self.assertEqual(value['source'], 'local')
                self.assertEqual(shlex.split(value['suggestion']), case['argv'])
                # Syntactically valid failures are not retries or AI requests.
                self.assertIsNone(self.suggest(shlex.join(case['argv']), ai=True)['suggestion'])
        self.assertFalse((self.path / 'ai-prompt').exists())
        for line in (self.path / 'calls').read_text().splitlines():
            name, args = json.loads(line)
            profile = PROFILES[name]
            queries = [profile['help']] + ([profile['fresh_commands']] if profile.get('fresh_commands') else []) + [v['help'] for v in profile.get('commands', {}).values() if v.get('help')]
            self.assertIn(args, queries, (name, args))

    def test_useful_forms_and_literal_argument_preservation(self):
        pairs = [
            ('cargo buidl --release', ['cargo', 'build', '--release']),
            ('cargo build --releas', ['cargo', 'build', '--release']),
            ('pacman -Q --inof bash', ['pacman', '-Q', '--info', 'bash']),
            ('yay --qurey --info bash', ['yay', '--query', '--info', 'bash']),
            ('ls --human-readbale -la', ['ls', '--human-readable', '-la']),
            ("cp --verboes 'source file' 'destination file'", ['cp', '--verbose', 'source file', 'destination file']),
            ("grep --line-numbre -e '--recusrive' 'private file'", ['grep', '--line-number', '-e', '--recusrive', 'private file']),
            ("rg --ignore-csae -g '*.rs' 'hello world' src", ['rg', '--ignore-case', '-g', '*.rs', 'hello world', 'src']),
            ("head --liens=4 'a b'", ['head', '--lines=4', 'a b']),
            ("wl-copy --trim-newlien '$(touch nope)'", ['wl-copy', '--trim-newline', '$(touch nope)']),
            ('wl-paste --list-tpyes', ['wl-paste', '--list-types']),
            ('hyprctl -j monitros all', ['hyprctl', '-j', 'monitors', 'all']),
            ('wpctl get-voluem @DEFAULT_AUDIO_SINK@', ['wpctl', 'get-volume', '@DEFAULT_AUDIO_SINK@']),
            ('wpctl set-voluem @DEFAULT_AUDIO_SINK@ 5%+', ['wpctl', 'set-volume', '@DEFAULT_AUDIO_SINK@', '5%+']),
            ('bluetoothctl conenct 00:11:22:33:44:55', ['bluetoothctl', 'connect', '00:11:22:33:44:55']),
            ('mkinitcpio --listhoks', ['mkinitcpio', '--listhooks']),
            ('limine versoin', ['limine', 'version']),
            ('gpg --list-kesy someone@example.com', ['gpg', '--list-keys', 'someone@example.com']),
            ('openssl versoin -a', ['openssl', 'version', '-a']),
            ("openssl x509 -in 'my cert.pem' -noout -fingreprint", ['openssl', 'x509', '-in', 'my cert.pem', '-noout', '-fingerprint']),
            ("ffmpeg -i 'a b.mp4' -vcoedc libx264 -n 'out file.mp4'", ['ffmpeg', '-i', 'a b.mp4', '-vcodec', 'libx264', '-n', 'out file.mp4']),
            ("ffprobe -show_streasm 'a b.mp4'", ['ffprobe', '-show_streams', 'a b.mp4']),
            ('tldr --platfrom linux git', ['tldr', '--platform', 'linux', 'git']),
            ("lazygit --work-tree '/tmp/my repo' --print-config-dri", ['lazygit', '--work-tree', '/tmp/my repo', '--print-config-dir']),
            ('loginctl list-sessinos', ['loginctl', 'list-sessions']),
            ("curl --connect-tiemout 3 --url 'https://example.invalid/private'", ['curl', '--connect-timeout', '3', '--url', 'https://example.invalid/private']),
            ("watch --interavl 1 printf '--interavl'", ['watch', '--interval', '1', 'printf', '--interavl']),
        ]
        for line, expected in pairs:
            with self.subTest(line=line):
                self.assertEqual(self.suggest(line)['argv'], expected)

    def test_unsupported_destructive_ambiguous_and_runtime_forms_decline(self):
        lines = [
            'hyprctl dispatch exec terminal', 'hyprctl disptach exec terminal',
            'hyprctl --batch reload', 'hyprctl devices', 'hyprctl devices extra',
            'hyprctl monitros --unsupported', 'wpctl get-voluem',
            'wpctl get-volume nonexistent', 'bluetoothctl remvoe 00:11:22:33:44:55',
            'mkinitcpio --allpreset', 'mkinitcpio --listhoks -P',
            'limine bios-instal /dev/fake', 'gpg --delete-kesy person',
            'gpg --quie -- --list-keys', 'openssl genrsa', 'openssl gensra',
            'ffmpeg -i input -vcoedc libx264 -y output', 'ffmpeg -i missing output',
            'ffmpeg -i input -unknowntypo output', 'ffprobe -show_streams missing',
            'wl-paste --wacth sh -c echo', 'wl-copy --primary -- --trim-newlien',
            'wl-copy --primary --trim-newline', "wl-copy 'clipboard --trim-newlien'",
            'cp --verboes', 'cp --verboes only-one-file',
            'cargo clean', 'cargo cleen', 'cargo -Z unstable-options buidl',
            'pacman -S --inof bash', 'yay --sync --seach bash',
            'cp --froce src dst', 'cp --verboes --force src dst',
            'rsync --deleet src dst', 'date --ste now', 'bootctl instal',
            "grep --regexp '--line-numbre' file", 'head --lines',
            'ls --huma', 'watch -n 1 echo --interavl',
            'ls --human-readbale --unknown', 'ls --human-readbale | cat',
            'sudo ls --human-readbale', 'lss --all',
            'winget search foo', 'brew instal foo', 'pwsh --commnad foo',
        ]
        for line in lines:
            with self.subTest(line=line):
                self.assertIsNone(self.suggest(line, ai=True)['suggestion'])
        self.assertFalse((self.path / 'executed').exists())
        self.assertFalse((self.path / 'ai-prompt').exists())

    def test_ai_only_sees_command_syntax_and_revalidates_operands(self):
        result = self.suggest('wpctl volumezzz private-sink', ai=True, ADAPTER_AI_CHOICE='wpctl get-volume')
        self.assertEqual(result['argv'], ['wpctl', 'get-volume', 'private-sink'])
        prompt = (self.path / 'ai-prompt').read_text()
        self.assertNotIn('private-sink', prompt)
        self.assertIsNone(self.suggest('wpctl volumezzz', ai=True, ADAPTER_AI_CHOICE='wpctl get-volume')['suggestion'])

    def test_cargo_aliases_are_discovered_fresh(self):
        self.assertEqual(self.suggest('cargo buidl')['argv'], ['cargo', 'build'])
        data = json.loads(self.fixture_path.read_text())
        data['cargo']['["--list"]']['stdout'] += '\n    buidl                alias: check\n'
        self.fixture_path.write_text(json.dumps(data))
        self.assertIsNone(self.suggest('cargo buidl', ai=True)['suggestion'])
        self.assertFalse((self.path / 'ai-prompt').exists())

    def test_multicall_symlink_keeps_invocation_name(self):
        script = self.path / 'ls'
        script.rename(self.path / 'multicall')
        script.symlink_to(self.path / 'multicall')
        result = self.suggest('ls --human-readbale')
        self.assertEqual(result['argv'], ['ls', '--human-readable'])
        self.assertEqual(result['executable'], str(script))

    def test_missing_metadata_and_unadvertised_flags_decline(self):
        self.assertIsNone(self.suggest('ls --human-readbale', ADAPTER_METADATA_FAILURE='1')['suggestion'])
        data = json.loads(self.fixture_path.read_text())
        row = data['ls']['["--help"]']
        row['stdout'] = row['stdout'].replace('--human-readable', '--undocumented')
        self.fixture_path.write_text(json.dumps(data))
        self.assertIsNone(self.suggest('ls --human-readbale')['suggestion'])

    def test_supported_command_matches_bash_registry_and_excludes_other_platforms(self):
        result = subprocess.run([str(BINARY), 'supported'], capture_output=True, text=True, env=self.env, check=True)
        names = result.stdout.splitlines()
        self.assertEqual(len(names), len(set(names)))
        self.assertEqual(set(names), set(PROFILES) | {'git', 'docker', 'systemctl', 'journalctl', 'herdr', 'omarchy'})
        self.assertFalse(set(names) & {'brew','winget','scoop','choco','pwsh','powershell'})

    def test_bash_new_profiles_cancel_and_accept_exact_argv(self):
        for line, expected in [
            ("cp --verboes 'a b' 'c d'", ['--verbose','a b','c d']),
            ('hyprctl -j monitros', ['-j','monitors']),
            ('wpctl get-voluem @DEFAULT_AUDIO_SINK@', ['get-volume','@DEFAULT_AUDIO_SINK@']),
            ("ffprobe -show_streasm 'a b.mp4'", ['-show_streams','a b.mp4']),
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
