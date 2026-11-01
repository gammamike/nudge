"""Helpers for testing the Rust executable and its Bash integration."""
import os
from pathlib import Path
import pty
import select
import signal
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
BINARY = ROOT / 'target/release/nudge-rust'


class Shell:
    def __init__(self, array=False, user_rc=False):
        self.directory = tempfile.TemporaryDirectory()
        self.path = Path(self.directory.name)
        self.marker = self.path / "executed"
        binary = self.path / "herdr"
        binary.write_text('''#!/bin/bash
if [[ $* == --help ]]; then
  printf 'Common commands:\\n  herdr server stop                Stop the server\\n'
elif [[ $* == 'server --help' ]]; then
  printf 'Commands:\\n  stop                    Stop the server\\n'
elif [[ $* == 'server stop' ]]; then
  printf 'server stop\\n' >> "$NUDGE_TEST_MARKER"
  printf 'FAKE_SERVER_STOPPED\\n'
  exit 7
else
  printf 'unknown subcommand\\n' >&2
  exit 2
fi
''')
        binary.chmod(0o700)
        # Isolate catalog discovery; tests never invoke real system actions.
        omarchy = self.path / "omarchy"
        omarchy.write_text('#!/bin/bash\nprintf \'{"commands": []}\\n\'\n')
        omarchy.chmod(0o700)
        rc = self.path / "rc"
        # Isolate the tested backend if the user already enabled Nudge in bashrc.
        rc.write_text(("source ~/.bashrc\n" if user_rc else "") +
                      ('for _test_index in "${!PROMPT_COMMAND[@]}"; do\n  [[ ${PROMPT_COMMAND[_test_index]} == _nudge_prompt ]] && unset \'PROMPT_COMMAND[_test_index]\'\ndone\nPROMPT_COMMAND=("${PROMPT_COMMAND[@]}")\nunset _NUDGE_LOADED\n' if user_rc else "") +
                      f'export PATH="{self.path}:$PATH"\n'
                      'HISTFILE=/dev/null\nHISTCONTROL=ignoreboth\n'
                      '_observe() { LAST_STATUS=$?; return "$LAST_STATUS"; }\n' +
                      ('PROMPT_COMMAND=(_observe "${PROMPT_COMMAND[@]}")\n' if user_rc else
                       'PROMPT_COMMAND=(_observe)\n' if array else 'PROMPT_COMMAND=_observe\n') +
                      '_NUDGE_TEST_BEFORE=("${PROMPT_COMMAND[@]}")\n' +
                      'PS1="__READY__ "\n' +
                      f'source "{ROOT}/nudge.bash"\nsource "{ROOT}/nudge.bash"\n' +
                      '_test_prompt() { PS1="__READY__ "; }\nPROMPT_COMMAND+=(_test_prompt)\n')
        self.pid, self.fd = pty.fork()
        if self.pid == 0:
            env = dict(os.environ, NUDGE_CACHE_DIR=str(self.path / "cache"), NUDGE_LOCAL_ONLY="1",
                       NUDGE_CONFIG=str(self.path / "config.json"),
                       NUDGE_TEST_MARKER=str(self.marker), TERM="xterm-256color")
            os.execvpe("bash", ["bash", "--noprofile", "--rcfile", str(rc), "-i"], env)
        self.pending = b""
        try:
            self.until(b"__READY__ ")
        except BaseException:
            self.close()
            raise

    def send(self, text):
        os.write(self.fd, text)

    def until(self, needle, timeout=6):
        deadline = time.monotonic() + timeout
        while needle not in self.pending:
            if time.monotonic() > deadline:
                raise AssertionError(f"Missing {needle!r}; output={self.pending!r}")
            if select.select([self.fd], [], [], .05)[0]:
                self.pending += os.read(self.fd, 65536)
        end = self.pending.index(needle) + len(needle)
        result, self.pending = self.pending[:end], self.pending[end:]
        return result

    def command(self, command):
        self.send(command.encode() + b"\n")
        return self.until(b"__READY__ ")

    def close(self):
        try:
            os.kill(self.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        os.waitpid(self.pid, 0)
        os.close(self.fd)
        self.directory.cleanup()
