"""Bash confirmation, cancellation, history, and prompt-hook contracts."""
import unittest

from support import Shell


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
