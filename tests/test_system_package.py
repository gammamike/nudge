"""Exercise staged installation without root, real providers, or host changes."""
import importlib.util
import os
from pathlib import Path
import subprocess
import tarfile
import tempfile
import unittest

from support import BINARY, ROOT


class SystemPackageTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory(prefix='nudge-package-')
        self.addCleanup(directory.cleanup)
        self.path = Path(directory.name)
        self.home = self.path / 'home'
        self.home.mkdir()
        (self.home / '.bashrc').write_text('# existing shell configuration\n')
        self.stage = self.path / 'stage with spaces'
        self.notices = self.path / 'notices'
        (self.notices / 'licenses').mkdir(parents=True)
        (self.notices / 'THIRD_PARTY_NOTICES.md').write_text('Test fixture only\n')
        (self.notices / 'licenses/example.txt').write_text('Test fixture only\n')
        self.env = dict(os.environ, HOME=str(self.home), HISTFILE='/dev/null',
                        XDG_CONFIG_HOME=str(self.home / 'config'),
                        XDG_CACHE_HOME=str(self.home / 'cache'),
                        XDG_DATA_HOME=str(self.home / 'data'))
        self.arguments = ['make', '-C', str(ROOT), f'DESTDIR={self.stage}', 'PREFIX=/usr',
                          f'BINARY={BINARY}', f'NOTICE_DIR={self.notices}']

    def install(self):
        subprocess.run([*self.arguments, 'install'], env=self.env, check=True, capture_output=True, timeout=30)
        return self.stage / 'usr/bin/nudge-bash'

    def test_stage_activation_lifecycle_guard_and_removal(self):
        binary = self.install()
        self.install()
        root = self.stage / 'usr/lib/nudge-bash'
        self.assertEqual(binary.resolve(), root / 'bin/nudge')
        self.assertTrue((root / 'package-managed').is_file())
        self.assertTrue((self.stage / 'usr/share/man/man1/nudge-bash.1').is_file())
        result = subprocess.run([str(binary), '--version'], env=self.env, text=True, capture_output=True, check=True)
        self.assertTrue(result.stdout.startswith('nudge '))
        command = 'source "$1"; [[ $_NUDGE_BINARY == "$2" && $_NUDGE_LOADED == 1 ]]'
        subprocess.run(['bash', '--noprofile', '--norc', '-ic', command, 'bash', str(root / 'nudge.bash'), str(root / 'bin/nudge')],
                       env=self.env, capture_output=True, check=True)
        for action in ['install', 'uninstall', 'rollback']:
            result = subprocess.run([str(binary), action, '--prefix', str(self.path / 'other')],
                                    env=self.env, text=True, capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('managed externally', result.stderr)
        self.assertFalse((self.path / 'other').exists())
        self.assertEqual(list(self.home.iterdir()), [self.home / '.bashrc'])
        (self.home / 'config/nudge').mkdir(parents=True)
        settings = self.home / 'config/nudge/config.json'
        settings.write_text('{"provider":"claude"}\n')
        subprocess.run([*self.arguments, 'uninstall'], env=self.env, check=True, capture_output=True, timeout=30)
        self.assertFalse(binary.exists())
        self.assertFalse(root.exists())
        self.assertTrue(settings.is_file())
        self.assertEqual((self.home / '.bashrc').read_text(), '# existing shell configuration\n')

    def test_completion_does_not_invoke_commands(self):
        completion = ROOT / 'completions/nudge-bash'
        script = 'source "$1"; COMP_WORDS=(nudge-bash config --provider cl); COMP_CWORD=3; _nudge_bash_complete; printf "%s\\n" "${COMPREPLY[@]}"'
        result = subprocess.run(['bash', '--noprofile', '--norc', '-c', script, 'bash', str(completion)],
                                env=self.env, capture_output=True, text=True, check=True)
        self.assertEqual(result.stdout, 'claude\n')

    def test_release_identity_and_checksum_fail_closed(self):
        spec = importlib.util.spec_from_file_location('verify_release', ROOT / 'scripts/verify-release.py')
        release = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(release)
        import hashlib
        import io
        dist = self.path / 'dist'
        dist.mkdir()
        def archive(name, path, text):
            with tarfile.open(dist / name, 'w:gz') as tar:
                data = text.encode()
                item = tarfile.TarInfo(path)
                item.size = len(data)
                tar.addfile(item, io.BytesIO(data))
        source = 'nudge-1.2.3-source.tar.gz'
        binary = 'nudge-1.2.3-linux-x86_64.tar.gz'
        archive(source, 'nudge-1.2.3-source/Cargo.toml', '[package]\nversion="1.2.3"\n')
        archive(binary, 'nudge-1.2.3-linux-x86_64/BUILD-INFO', 'version=1.2.3\ntarget=x86_64-unknown-linux-musl\ncommit=abc\ndirty=false\n')
        (dist / 'SHA256SUMS').write_text(''.join(hashlib.sha256((dist / n).read_bytes()).hexdigest() + '  ' + n + '\n' for n in [source, binary]))
        self.assertEqual(release.verify(dist, tag='v1.2.3', commit='abc')[0], '1.2.3')
        for arguments in [dict(tag='v1.2.4'), dict(commit='def')]:
            with self.assertRaises(ValueError):
                release.verify(dist, **arguments)
        archive(binary, 'nudge-1.2.3-linux-x86_64/BUILD-INFO', 'version=1.2.3\ntarget=x86_64-unknown-linux-musl\ncommit=abc\ndirty=true\n')
        (dist / 'SHA256SUMS').write_text(''.join(hashlib.sha256((dist / n).read_bytes()).hexdigest() + '  ' + n + '\n' for n in [source, binary]))
        with self.assertRaisesRegex(ValueError, 'Development artifacts'):
            release.verify(dist)
        self.assertEqual(release.verify(dist, allow_development=True)[0], '1.2.3')
        (dist / source).write_bytes(b'changed archive')
        with self.assertRaisesRegex(ValueError, 'Checksum mismatch'):
            release.verify(dist)
