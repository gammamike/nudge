"""Verify explicit desktop setup with release fixtures and no network access."""
import hashlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile
import unittest

from support import BINARY, ROOT


class CompanionSetupTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix='nudge-setup-')
        self.addCleanup(self.directory.cleanup)
        self.home = Path(self.directory.name)
        self.bin = self.home / 'bin'
        self.bin.mkdir()
        for name in ('jq', 'curl', 'tar', 'gzip', 'sha256sum', 'timeout', 'flock', 'mktemp',
                     'mkdir', 'cat', 'chmod', 'cmp', 'ln', 'rm', 'uname'):
            if name != 'curl':
                self.bin.joinpath(name).symlink_to(shutil.which(name))
        self.env = {'HOME': str(self.home), 'PATH': str(self.bin), 'LC_ALL': 'C',
                    'NUDGE_LOCAL_ONLY': '1', 'XDG_DATA_HOME': str(self.home / 'data'),
                    'XDG_STATE_HOME': str(self.home / 'state')}
        self.rc = self.home / '.bashrc'
        self.rc.write_text('# preserve my settings\n')
        self.version = json.loads((ROOT / 'manifest.json').read_text())['version']
        self.archive = self.home / 'bundle.tar.gz'
        self.make_archive()
        curl = self.bin / 'curl'
        curl.write_text('''#!/bin/bash
printf '%s\\n' "$*" >> "$HOME/downloads"
for ((i=1; i<=$#; i++)); do
  if [[ ${!i} == --output ]]; then ((i++)); output=${!i}; fi
done
case "${!#}" in
  https://github.com/gammamike/nudge/releases/download/v*/SHA256SUMS) /bin/cat "$HOME/SHA256SUMS" > "$output" ;;
  https://github.com/gammamike/nudge/releases/download/v*/nudge-*-linux-x86_64.tar.gz) /bin/cat "$HOME/bundle.tar.gz" > "$output" ;;
  *) exit 22 ;;
esac
''')
        curl.chmod(0o700)

    def make_archive(self, special=None, version=None):
        prefix = f'nudge-{self.version}-linux-x86_64'
        with tarfile.open(self.archive, 'w:gz') as archive:
            if version:
                content = f'#!/bin/bash\necho "nudge {version}"\n'.encode()
            else:
                content = BINARY.read_bytes()
            binary = tarfile.TarInfo(prefix + '/bin/nudge')
            binary.mode = 0o755
            binary.size = len(content)
            archive.addfile(binary, io.BytesIO(content))
            if special:
                member = tarfile.TarInfo(special)
                if special.endswith('symlink'):
                    member.type = tarfile.SYMTYPE
                    member.linkname = str(self.home / 'outside')
                archive.addfile(member)
        digest = hashlib.sha256(self.archive.read_bytes()).hexdigest()
        (self.home / 'SHA256SUMS').write_text(f'{digest}  {prefix}.tar.gz\n')

    def setup(self, success=True):
        result = subprocess.run(['/bin/bash', str(ROOT / 'companion/omarchy/bridge.sh'), 'setup'],
                                env=self.env, capture_output=True, text=True, timeout=30)
        if success:
            self.assertEqual(result.returncode, 0, result.stderr)
            return json.loads(result.stdout)
        self.assertNotEqual(result.returncode, 0, result.stdout)
        return result

    def test_install_hook_launcher_and_repeated_setup_preserves_settings(self):
        config = self.home / '.config/nudge/config.json'
        config.parent.mkdir(parents=True)
        config.write_text('{"provider":"claude","models":{"claude":"haiku"}}')
        original_config = config.read_bytes()
        result = self.setup()
        self.assertTrue(result['available'])
        self.assertTrue(result['launcher']['installed'])
        self.assertIn('# preserve my settings', self.rc.read_text())
        self.assertEqual(self.rc.read_text().count('# >>> nudge managed setup >>>'), 1)
        self.assertTrue(list(self.home.glob('.bashrc.nudge-backup-*')))
        downloads = (self.home / 'downloads').read_text()
        self.assertIn('--proto =https --proto-redir =https', downloads)
        self.setup()
        self.assertEqual((self.home / 'downloads').read_text(), downloads)
        self.assertEqual(config.read_bytes(), original_config)
        self.assertEqual(self.rc.read_text().count('# >>> nudge managed setup >>>'), 1)
        env = dict(self.env, PATH='/usr/bin:/bin', HISTFILE='/dev/null')
        result = subprocess.run(['/bin/bash', '--noprofile', '--rcfile', str(self.rc), '-ic',
                                 '[[ $_NUDGE_LOADED == 1 && ${PROMPT_COMMAND[0]} == _nudge_prompt ]]'],
                                env=env, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_bad_checksums_and_download_failures_leave_shell_untouched(self):
        for checksums in ('invalid\n', '0' * 64 + f'  nudge-{self.version}-linux-x86_64.tar.gz\n'):
            (self.home / 'SHA256SUMS').write_text(checksums)
            self.setup(success=False)
            self.assertEqual(self.rc.read_text(), '# preserve my settings\n')
            self.assertFalse((self.home / 'data/nudge').exists())
        (self.home / 'SHA256SUMS').unlink()
        self.setup(success=False)
        self.assertFalse((self.home / 'data/applications').exists())

    def test_unsafe_archives_and_wrong_versions_do_not_install(self):
        for member in (f'nudge-{self.version}-linux-x86_64/../../outside',
                       f'nudge-{self.version}-linux-x86_64/symlink', '/absolute'):
            self.make_archive(special=member)
            self.setup(success=False)
            self.assertEqual(self.rc.read_text(), '# preserve my settings\n')
            self.assertFalse((self.home / 'outside').exists())
        self.make_archive(version='99.0.0')
        self.setup(success=False)
        self.assertFalse((self.home / 'data/nudge').exists())

    def test_existing_launcher_and_package_conflicts_are_preserved(self):
        desktop = self.home / 'data/applications/gammamike.nudge.desktop'
        desktop.parent.mkdir(parents=True)
        desktop.write_text('custom launcher')
        self.setup(success=False)
        self.assertEqual(desktop.read_text(), 'custom launcher')
        self.assertFalse((self.home / 'downloads').exists())
        desktop.unlink()
        (self.bin / 'nudge-bash').symlink_to(BINARY)
        self.assertIn('package or custom path', self.setup(success=False).stderr)
        self.assertFalse((self.home / 'downloads').exists())
        self.assertEqual(self.rc.read_text(), '# preserve my settings\n')

    def test_welcome_marker_is_read_only_until_panel_is_opened(self):
        helper = str(ROOT / 'companion/omarchy/welcome.sh')
        def invoke(action):
            return subprocess.run(['/bin/bash', helper, action], env=self.env,
                                  check=True, capture_output=True, text=True).stdout
        self.assertEqual(json.loads(invoke('status')), {'seen': False})
        self.assertFalse((self.home / 'state').exists())
        invoke('mark')
        self.assertEqual(json.loads(invoke('status')), {'seen': True})
        invoke('mark')
        self.env['XDG_STATE_HOME'] = 'relative'
        self.assertEqual(json.loads(invoke('status')), {'seen': False})
        invoke('mark')
        self.assertTrue((self.home / '.local/state/nudge/companion-welcome-seen').is_dir())
