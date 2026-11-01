import importlib.util
import json
import os
from pathlib import Path
import pty
import select
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("nudge", ROOT / "nudge.py")
nudge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(nudge)


def entry(command, args=""):
    return {"argv": command.split(), "args": args, "summary": command, "source": "test"}


DATA = {"binaries": {"herdr": ["/usr/bin/herdr"], "omarchy": ["/usr/bin/omarchy"]},
        "entries": [entry("herdr server stop"), entry("herdr server reload-config"),
                    entry("herdr session attach", "<name>"),
                    entry("omarchy restart terminal"), entry("omarchy theme list"),
                    entry("omarchy theme set", "<theme-name>"),
                    entry("omarchy toggle nightlight", "[--status]"),
                    entry("omarchy system shutdown")]}


class EngineTests(unittest.TestCase):
    def setUp(self):
        self.catalog = patch.object(nudge, "catalog", return_value=DATA)
        self.catalog.start()
        self.addCleanup(self.catalog.stop)

    def test_missing_subcommand_and_typos(self):
        for text, expected in [("herdr stop", "herdr server stop"),
                               ("omarchy restart terminl", "omarchy restart terminal"),
                               ("omarchy nightlight", "omarchy toggle nightlight"),
                               ("omarchy theme lsit", "omarchy theme list")]:
            with self.subTest(text=text):
                result = nudge.suggest(text, local_only=True)
                self.assertEqual(result["suggestion"], expected)
                self.assertEqual(result["source"], "local")

    def test_no_inference_for_success_interrupt_or_unsupported_syntax(self):
        with patch.object(nudge, "codex_pick") as ai:
            for text in ("echo failed", "herdr stop; touch /tmp/oops", "herdr $(id)",
                         "herdr stop | cat", "herdr stop\ntrue", "herdr --session foo stop",
                         "sudo herdr stop", "herdr server stop", "omarchy theme",
                         "omarchy theme set nord", "omarchy theme sett nord",
                         "omarchy system shutdow", "omarchy shutdown"):
                result = nudge.suggest(text, local_only=True)
                self.assertIsNone(result["suggestion"], text)
            for status in (0, 130):
                self.assertIsNone(nudge.suggest("herdr stop", status=status)["suggestion"])
            ai.assert_not_called()

    def test_ambiguous_local_match_abstains(self):
        data = {**DATA, "entries": DATA["entries"] + [entry("herdr session stop")]}
        with patch.object(nudge, "catalog", return_value=data):
            self.assertIsNone(nudge.suggest("herdr stop", local_only=True)["suggestion"])

    def test_ai_only_after_local_abstains(self):
        with patch.object(nudge, "codex_pick", return_value=(DATA["entries"][0], None)) as ai:
            self.assertEqual(nudge.suggest("herdr stop")["source"], "local")
            ai.assert_not_called()
            result = nudge.suggest("herdr halt")
            self.assertEqual(result["source"], "codex")
            self.assertEqual(result["suggestion"], "herdr server stop")
            ai.assert_called_once()

    def test_api_keys_not_forwarded(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sentinel", "CODEX_API_KEY": "sentinel",
                                     "CODEX_THREAD_ID": "sentinel"}):
            env = nudge.codex_environment()
            for key in ("OPENAI_API_KEY", "CODEX_API_KEY", "CODEX_THREAD_ID"):
                self.assertNotIn(key, env)

    def test_api_auth_refused(self):
        auth = subprocess.CompletedProcess([], 0, "", "Logged in using an API key")
        with patch.object(nudge, "run", return_value=auth) as run:
            picked, reason = nudge.codex_pick(["herdr", "halt"], DATA["entries"])
            self.assertIsNone(picked)
            self.assertIn("API billing is disabled", reason)
            self.assertEqual(run.call_count, 1)

    def test_model_cannot_supply_arbitrary_command(self):
        auth = subprocess.CompletedProcess([], 0, "Logged in using ChatGPT", "")

        def fake_run(argv, **kwargs):
            if "status" in argv:
                return auth
            Path(argv[argv.index("-o") + 1]).write_text('{"candidate_id": 999}')
            return subprocess.CompletedProcess([], 0, "", "")

        with tempfile.TemporaryDirectory() as directory, patch.object(nudge, "CACHE", Path(directory)):
            with patch.object(nudge, "run", side_effect=fake_run):
                picked, reason = nudge.codex_pick(["herdr", "halt"], DATA["entries"])
                self.assertIsNone(picked)
                self.assertEqual(reason, "Codex declined")


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
        # Avoid loading the real Omarchy catalog; tests never invoke real actions.
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


class ShellTests(unittest.TestCase):
    def shell(self, **kwargs):
        shell = Shell(**kwargs)
        self.addCleanup(shell.close)
        return shell

    def test_enter_executes_once_and_preserves_original_exit(self):
        shell = self.shell(array=True)
        shell.send(b"herdr stop\n")
        output = shell.until(b"Any other key to cancel ")
        self.assertIn(b"herdr server stop", output)
        self.assertFalse(shell.marker.exists())
        shell.send(b"\n")
        self.assertIn(b"FAKE_SERVER_STOPPED", shell.until(b"__READY__ "))
        self.assertEqual(shell.marker.read_text(), "server stop\n")
        self.assertIn(b"STATUS=2 CORRECTION=7", shell.command(
            'printf "STATUS=%s CORRECTION=%s\\n" "$LAST_STATUS" "$NUDGE_LAST_CORRECTION_STATUS"'))

    def test_cancel_preserves_failure_and_never_executes(self):
        shell = self.shell()
        shell.send(b"herdr stop\n")
        shell.until(b"Any other key to cancel ")
        shell.send(b"x")
        self.assertIn(b"Cancelled.", shell.until(b"__READY__ "))
        self.assertFalse(shell.marker.exists())
        self.assertIn(b"STATUS=2", shell.command('printf "STATUS=%s\\n" "$LAST_STATUS"'))
        self.assertIn(b"ignoreboth", shell.command('printf "%s\\n" "$HISTCONTROL"'))

    def test_arrow_cancels_without_leaking_escape_sequence(self):
        shell = self.shell()
        shell.send(b"herdr stop\n")
        shell.until(b"Any other key to cancel ")
        shell.send(b"\x1b[A")
        shell.until(b"__READY__ ")
        self.assertIn(b"CLEAN", shell.command('printf "CLEAN\\n"'))
        self.assertFalse(shell.marker.exists())

    def test_history_ignored_command_does_not_reuse_previous_failure(self):
        shell = self.shell()
        self.assertNotIn(b"nudge [", shell.command(" herdr stop"))
        self.assertNotIn(b"nudge [", shell.command("false"))
        self.assertFalse(shell.marker.exists())

    def test_no_prompt_on_valid_command_failure_or_pipeline(self):
        shell = self.shell()
        self.assertNotIn(b"nudge [", shell.command("herdr server stop"))
        self.assertNotIn(b"nudge [", shell.command("herdr stop | false"))
        self.assertEqual(shell.marker.read_text(), "server stop\n")

    def test_user_bashrc_hooks_still_present_and_cancel_works(self):
        shell = self.shell(user_rc=True)
        output = shell.command('for i in "${!_NUDGE_TEST_BEFORE[@]}"; do '
                               '[[ ${PROMPT_COMMAND[i+1]} == "${_NUDGE_TEST_BEFORE[i]}" ]] '
                               '|| printf "LOST\\n"; done')
        self.assertNotIn(b"\r\nLOST\r\n", output)
        shell.send(b"herdr stop\n")
        shell.until(b"Any other key to cancel ")
        shell.send(b"n")
        shell.until(b"__READY__ ")
        self.assertFalse(shell.marker.exists())

    def test_ctrl_c_restores_terminal(self):
        shell = self.shell()
        shell.send(b"herdr stop\n")
        shell.until(b"Any other key to cancel ")
        shell.send(b"\x03")
        shell.until(b"__READY__ ")
        self.assertFalse(shell.marker.exists())
        self.assertIn(b"ALIVE", shell.command('printf "ALIVE\\n"'))


if __name__ == "__main__":
    unittest.main(verbosity=2)
