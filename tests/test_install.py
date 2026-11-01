"""Exercise installed Rust binaries and Bash hooks in disposable home directories."""
import json
import os
from pathlib import Path
import pty
import select
import shutil
import signal
import subprocess
import tempfile
import time
import unittest

from support import BINARY, ROOT


class InstallTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name)
        self.home = self.path / "home with 'quotes' $(literal)"
        self.home.mkdir()
        self.rc = self.home / '.bashrc'
        self.original = '# personal settings\nexport RETAIN_ME=yes'  # no final newline
        self.rc.write_text(self.original)
        self.rc.chmod(0o640)
        self.env = {k:v for k,v in os.environ.items() if not k.startswith(('NUDGE_', 'XDG_'))}
        self.env.update(HOME=str(self.home), HISTFILE='/dev/null', NUDGE_LOCAL_ONLY='1')
        metadata=self.path/'metadata';metadata.mkdir()
        for name,text in {'herdr': "#!/bin/bash\nexit 0\n", 'omarchy': "#!/bin/bash\nprintf '{\"commands\": []}\\n'\n"}.items():
            tool=metadata/name;tool.write_text(text);tool.chmod(0o755)
        self.env['PATH']=str(metadata)+':'+os.environ['PATH']
        self.root = self.home / '.local/share/nudge'
        self.binary = self.home / '.local/bin/nudge'

    def run_nudge(self, *args, executable=None, ok=True, **updates):
        r = subprocess.run([str(executable or BINARY), *map(str,args)], env=dict(self.env, **updates),
                           text=True, capture_output=True, timeout=10)
        if ok:self.assertEqual(r.returncode,0,r.stderr)
        else:self.assertNotEqual(r.returncode,0,r.stdout)
        return r

    def test_bundle_notices_are_retained_after_removing_download(self):
        bundle=self.path/'bundle';(bundle/'bin').mkdir(parents=True)
        shutil.copy2(BINARY,bundle/'bin/nudge')
        (bundle/'licenses').mkdir();(bundle/'licenses/dependency.txt').write_text('dependency notice')
        (bundle/'THIRD_PARTY_NOTICES.md').write_text('notice index')
        self.run_nudge('install',executable=bundle/'bin/nudge')
        shutil.rmtree(bundle)
        self.assertEqual((self.root/'current/licenses/dependency.txt').read_text(),'dependency notice')
        self.assertEqual((self.root/'current/THIRD_PARTY_NOTICES.md').read_text(),'notice index')
        self.assertEqual(self.run_nudge('supported',executable=self.binary).stdout, self.run_nudge('supported').stdout)

    def test_edited_hook_blocks_updates_and_unknown_files_block_removal(self):
        self.run_nudge('install')
        current=os.readlink(self.root/'current')
        rc=self.rc.read_text();self.rc.write_text(rc.replace('# <<< nudge managed setup <<<','# modified'))
        self.run_nudge('install',ok=False)
        self.assertEqual(os.readlink(self.root/'current'),current)
        self.rc.write_text(rc)
        (self.root/'personal.txt').write_text('preserve')
        self.run_nudge('uninstall',executable=self.binary,ok=False)
        self.assertEqual(self.rc.read_text(),rc)
        self.assertEqual((self.root/'personal.txt').read_text(),'preserve')

    def test_install_idempotency_and_uninstall_preserve_user_data(self):
        self.run_nudge('install')
        self.assertEqual(self.run_nudge('--version',executable=self.binary).stdout,self.run_nudge('--version').stdout)
        installed = self.rc.read_text()
        self.assertEqual(installed.count('# >>> nudge managed setup >>>'),1)
        self.assertEqual(self.rc.stat().st_mode & 0o777,0o640)
        self.assertEqual(len(list(self.home.glob('.bashrc.nudge-backup-*'))),1)
        current = os.readlink(self.root/'current')
        self.run_nudge('install',executable=self.binary)
        self.assertEqual(os.readlink(self.root/'current'),current)
        self.assertEqual(self.rc.read_text(),installed)
        self.assertEqual(len(list((self.root/'releases').iterdir())),1)
        config = self.home/'.config/nudge/config.json';config.parent.mkdir(parents=True);config.write_text('private settings')
        cache = self.home/'.cache/nudge/keep';cache.parent.mkdir(parents=True);cache.write_text('cached data')
        self.rc.write_text(installed+'\n# added after installation\n')
        self.run_nudge('install',executable=self.binary)
        self.assertEqual(self.rc.read_text(),installed+'\n# added after installation\n')
        self.run_nudge('uninstall',executable=self.binary)
        self.assertEqual(self.rc.read_text(),self.original+'\n# added after installation\n')
        self.assertFalse(self.binary.exists());self.assertFalse(self.root.exists())
        self.assertEqual(config.read_text(),'private settings');self.assertEqual(cache.read_text(),'cached data')
        self.run_nudge('uninstall')

    def test_prefix_no_shell_modification_and_installed_location_inference(self):
        prefix=self.path/'custom prefix'
        self.run_nudge('install','--prefix',prefix,'--no-modify-shell')
        binary=prefix/'bin/nudge'
        self.assertTrue(binary.is_file());self.assertEqual(self.rc.read_text(),self.original)
        self.run_nudge('uninstall',executable=binary)
        self.assertFalse(binary.exists());self.assertFalse((prefix/'share/nudge').exists())

    def test_xdg_defaults_and_relative_xdg_values(self):
        data=self.path/'data';config=self.path/'config';cache=self.path/'cache'
        updates=dict(XDG_DATA_HOME=str(data),XDG_CONFIG_HOME=str(config),XDG_CACHE_HOME=str(cache))
        self.run_nudge('install',**updates)
        self.assertTrue((data/'nudge/current/bin/nudge').exists())
        shown=json.loads(self.run_nudge('config',executable=self.binary,**updates).stdout)
        self.assertEqual(shown['path'],str(config/'nudge/config.json'))
        self.run_nudge('refresh',executable=self.binary,**updates)
        self.assertTrue((cache/'nudge/catalog.json').is_file())
        self.run_nudge('uninstall',executable=self.binary,**updates)
        self.run_nudge('install',XDG_DATA_HOME='relative',XDG_CONFIG_HOME='relative',XDG_CACHE_HOME='relative')
        self.assertTrue(self.root.is_dir())
        shown=json.loads(self.run_nudge('config',XDG_CONFIG_HOME='relative').stdout)
        self.assertEqual(shown['path'],str(self.home/'.config/nudge/config.json'))

    def test_updates_and_rollback_keep_previous_release(self):
        first=self.path/'first';shutil.copy2(BINARY,first)
        self.run_nudge('install',executable=first)
        old=os.readlink(self.root/'current')
        second=self.path/'second';shutil.copy2(BINARY,second)
        # ELF permits trailing bytes; distinguish payloads without running a real operation.
        with second.open('ab') as f:f.write(b'\ninstallation update test\n')
        self.run_nudge('install',executable=second)
        new=os.readlink(self.root/'current');self.assertNotEqual(new,old)
        self.assertEqual(os.readlink(self.root/'previous'),old)
        first.unlink();second.unlink()  # installed copies are independent of their source
        self.run_nudge('rollback',executable=self.binary)
        self.assertEqual(os.readlink(self.root/'current'),old)
        self.assertEqual(os.readlink(self.root/'previous'),new)
        self.run_nudge('rollback',executable=self.binary)
        self.assertEqual(os.readlink(self.root/'current'),new)

    def test_conflicts_symlinks_and_edited_blocks_are_preserved(self):
        self.binary.parent.mkdir(parents=True);self.binary.write_text('unrelated program')
        self.run_nudge('install',ok=False)
        self.assertEqual(self.binary.read_text(),'unrelated program');self.assertEqual(self.rc.read_text(),self.original)
        self.binary.unlink()
        real=self.home/'dotfiles';self.rc.rename(real);self.rc.symlink_to(real)
        self.run_nudge('install',ok=False)
        self.assertTrue(self.rc.is_symlink());self.assertEqual(real.read_text(),self.original)
        self.run_nudge('install','--no-modify-shell')
        self.run_nudge('uninstall',executable=self.binary)
        self.rc.unlink();real.rename(self.rc)
        self.run_nudge('install')
        self.rc.write_text(self.rc.read_text().replace('# <<< nudge managed setup <<<','# custom ending'))
        self.run_nudge('uninstall',executable=self.binary,ok=False)
        self.assertTrue(self.binary.exists());self.assertIn('# custom ending',self.rc.read_text())

    def test_unmanaged_directories_and_external_links_decline(self):
        self.root.mkdir(parents=True);(self.root/'personal').write_text('keep')
        self.run_nudge('install',ok=False);self.assertEqual((self.root/'personal').read_text(),'keep')
        shutil.rmtree(self.root)
        outside=self.path/'outside';outside.mkdir();(outside/'keep').write_text('safe')
        self.root.symlink_to(outside,target_is_directory=True)
        self.run_nudge('install',ok=False);self.run_nudge('uninstall',ok=False)
        self.assertEqual((outside/'keep').read_text(),'safe')
        self.root.unlink();self.run_nudge('install')
        (self.root/'previous').symlink_to(outside,target_is_directory=True)
        self.run_nudge('rollback',executable=self.binary,ok=False)
        self.assertEqual((outside/'keep').read_text(),'safe')

    def test_lock_missing_previous_and_replaced_launcher(self):
        self.run_nudge('install')
        self.run_nudge('rollback',executable=self.binary,ok=False)
        (self.root/'.lock').write_text('other process')
        self.run_nudge('install',executable=self.binary,ok=False)
        self.run_nudge('uninstall',executable=self.binary,ok=False)
        (self.root/'.lock').unlink()
        installed=self.binary.resolve()
        self.binary.unlink();self.binary.write_text('new unrelated program')
        self.run_nudge('uninstall',executable=installed)
        self.assertEqual(self.binary.read_text(),'new unrelated program')

    def test_missing_bashrc_and_explicit_bashrc(self):
        self.rc.unlink();custom=self.home/'custom.bashrc'
        self.run_nudge('install','--bashrc',custom)
        self.assertFalse(self.rc.exists());self.assertTrue(custom.exists())
        self.run_nudge('uninstall',executable=self.binary)
        self.assertEqual(custom.read_text(),'')

    def test_invalid_install_options_do_not_change_shell(self):
        for args in [('install','--prefix','relative'),('install','--prefix',str(self.path/'bad:prefix')),
                     ('install','--bashrc','relative'),('install','--no-modify-shell','--bashrc',str(self.rc)),
                     ('uninstall','--purge'),('rollback','--no-modify-shell')]:
            with self.subTest(args=args):self.run_nudge(*args,ok=False)
        self.assertEqual(self.rc.read_text(),self.original)

    def test_installed_hook_cancel_accept_and_prompt_preservation(self):
        self.rc.write_text('PROMPT_COMMAND=("printf HOOK_OK")\nPS1="__READY__ "\nHISTCONTROL=ignoreboth\n')
        self.run_nudge('install')
        mocks=self.home/'mocks';mocks.mkdir();marker=self.home/'executed'
        tool=mocks/'git';tool.write_text('''#!/usr/bin/env bash
if [[ $1 == --list-cmds=main,others,alias ]]; then printf 'status\\n'; exit 0; fi
if [[ $1 == status && $2 == -h ]]; then printf 'usage: git status\\n'; exit 129; fi
if [[ $1 == status ]]; then printf 'ACCEPTED_TEST_COMMAND\\n'; printf 'status\\n' >> "$NUDGE_TEST_MARKER"; exit 7; fi
exit 2
''');tool.chmod(0o755)
        pid,fd=pty.fork()
        if pid==0:
            env=dict(self.env,PATH=f"{mocks}:{os.environ['PATH']}",TERM='dumb',NUDGE_TEST_MARKER=str(marker))
            os.execve('/bin/bash',['bash','--noprofile','--rcfile',str(self.rc),'-i'],env)
        pending=b''
        def until(needle):
            nonlocal pending
            deadline=time.monotonic()+8
            while needle not in pending:
                self.assertLess(time.monotonic(),deadline,pending[-1500:])
                if select.select([fd],[],[],.05)[0]:pending+=os.read(fd,65536)
            stop=pending.index(needle)+len(needle);found,pending=pending[:stop],pending[stop:];return found
        try:
            self.assertIn(b'HOOK_OK',until(b'__READY__ '))
            os.write(fd,b'git statsu\n');until(b'Any other key to cancel ')
            self.assertFalse(marker.exists());os.write(fd,b'x');until(b'__READY__ ')
            self.assertFalse(marker.exists());os.write(fd,b':\n');until(b'__READY__ ')
            os.write(fd,b'git statsu\n');until(b'Any other key to cancel ');os.write(fd,b'\n')
            self.assertIn(b'ACCEPTED_TEST_COMMAND',until(b'__READY__ '));self.assertEqual(marker.read_text(),'status\n')
        finally:
            os.kill(pid,signal.SIGKILL);os.waitpid(pid,0);os.close(fd)
