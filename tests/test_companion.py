"""Exercise the desktop adapter with the real CLI in disposable homes."""
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import tomllib
import unittest

from support import BINARY, ROOT


class CompanionTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="nudge companion ")
        self.addCleanup(self.directory.cleanup)
        self.home = Path(self.directory.name)
        self.bin = self.home / "bin"
        self.bin.mkdir()
        for name in ("jq", "timeout"):
            self.bin.joinpath(name).symlink_to(shutil.which(name))
        self.bin.joinpath("nudge-bash").symlink_to(BINARY)
        self.config = self.home / "config" / "nudge" / "config.json"
        self.env = {
            "HOME": str(self.home), "PATH": str(self.bin), "LC_ALL": "C",
            "XDG_CONFIG_HOME": str(self.home / "config"),
            "XDG_DATA_HOME": str(self.home / "data"),
        }
        self.rc = self.home / ".bashrc"
        self.rc.write_text("# existing user settings\n")

    def run_bridge(self, *args, success=True):
        result = subprocess.run(
            ["/bin/bash", str(ROOT / "companion/omarchy/bridge.sh"), *args],
            env=self.env, capture_output=True, text=True, timeout=20,
        )
        self.assertEqual(self.rc.read_text(), "# existing user settings\n")
        if success:
            self.assertEqual(result.returncode, 0, result.stderr)
            return json.loads(result.stdout)
        self.assertNotEqual(result.returncode, 0, result.stdout)
        return result

    def test_read_does_not_create_configuration(self):
        status = self.run_bridge("status")
        self.assertTrue(status["available"])
        self.assertEqual(status["settings"]["path"], str(self.config))
        self.assertFalse(self.config.exists())

    def test_each_provider_saved_and_reloaded_without_losing_others(self):
        for provider, model, endpoint in (
            ("codex", "account-model", ""),
            ("claude", "haiku", ""),
            ("ollama", "qwen3:0.6b", "http://127.0.0.1:11434"),
            ("local", "local/model", "http://127.0.0.1:1234/v1"),
        ):
            with self.subTest(provider=provider):
                result = self.run_bridge("save", provider, model, endpoint)
                self.assertEqual(result["settings"]["provider"], provider)
                self.assertEqual(result["settings"]["model"], model)
                self.assertEqual(result, self.run_bridge("status"))
        config = json.loads(self.config.read_text())
        self.assertEqual(len(config["models"]), 4)
        self.assertEqual(len(config["endpoints"]), 2)
        self.assertEqual(self.config.stat().st_mode & 0o777, 0o600)

    def test_blank_fields_keep_saved_values_and_environment_is_separate(self):
        self.run_bridge("save", "claude", "haiku", "")
        self.env["NUDGE_PROVIDER"] = "codex"
        status = self.run_bridge("save", "claude", "", "")
        self.assertEqual(status["settings"]["config"]["provider"], "claude")
        self.assertEqual(status["settings"]["config"]["models"]["claude"], "haiku")
        self.assertEqual(status["settings"]["provider"], "codex")

    def test_bad_values_fail_without_writing_or_shell_execution(self):
        for args in (
            ("save", "unknown", "model", ""),
            ("save", "codex", "$(touch PWNED)", ""),
            ("save", "claude", "--help", ""),
            ("save", "codex", "model", "http://127.0.0.1:1234"),
            ("save", "local", "model", "https://example.com/v1"),
            ("save", "local", "model", "http://user:password@127.0.0.1:1234/v1"),
            ("save", "local"),
            ("status", "extra"),
            ("uninstall",),
        ):
            with self.subTest(action=args):
                self.run_bridge(*args, success=False)
                self.assertFalse(self.config.exists())

    def test_missing_install_ignores_unrelated_nudge(self):
        if any(Path(prefix, "lib/nudge-bash/bin/nudge").exists()
               for prefix in ("/usr", "/usr/local")):
            self.skipTest("system installation is intentionally discoverable")
        self.bin.joinpath("nudge-bash").unlink()
        unrelated = self.bin / "nudge"
        unrelated.write_text('#!/bin/bash\nprintf unsafe > "$HOME/executed"\n')
        unrelated.chmod(0o700)
        self.assertEqual(self.run_bridge("status"), {"available": False})
        self.assertFalse(self.home.joinpath("executed").exists())
        self.run_bridge("save", "codex", "model", "", success=False)

    def test_managed_user_install_discovery(self):
        self.bin.joinpath("nudge-bash").unlink()
        root = self.home / "data/nudge"
        binary = root / "current/bin/nudge"
        binary.parent.mkdir(parents=True)
        binary.symlink_to(BINARY)
        root.joinpath("install.json").write_text('{"format":1}')
        self.assertEqual(self.run_bridge("status")["binary"], str(binary))

    def test_relative_xdg_data_uses_home_default(self):
        self.bin.joinpath("nudge-bash").unlink()
        self.env["XDG_DATA_HOME"] = "relative-path"
        root = self.home / ".local/share/nudge"
        binary = root / "current/bin/nudge"
        binary.parent.mkdir(parents=True)
        binary.symlink_to(BINARY)
        root.joinpath("install.json").write_text('{"format":1}')
        self.assertEqual(self.run_bridge("status")["binary"], str(binary))

    def test_local_model_discovery_uses_cli_and_does_not_save(self):
        curl = self.bin / "curl"
        curl.write_text('''#!/bin/bash
printf '%s\\n' '{"models":[{"name":"qwen3:0.6b"},{"name":"cloud-model","remote_host":"remote.example"}],"data":[{"id":"local/model"}]}'
''')
        curl.chmod(0o700)
        self.assertEqual(self.run_bridge("models", "ollama", "")["models"], ["qwen3:0.6b"])
        self.assertEqual(self.run_bridge("models", "local", "")["models"], ["local/model"])
        self.run_bridge("models", "codex", "", success=False)
        self.run_bridge("models", "local", "http://example.com/v1", success=False)
        self.assertFalse(self.config.exists())

    def test_broken_configuration_and_timeout_are_errors(self):
        self.config.parent.mkdir(parents=True)
        self.config.write_text('{"unsupported":true}')
        self.run_bridge("status", success=False)
        self.bin.joinpath("timeout").unlink()
        timeout = self.bin / "timeout"
        timeout.write_text("#!/bin/bash\nexit 124\n")
        timeout.chmod(0o700)
        self.assertEqual(self.run_bridge("status", success=False).returncode, 124)

    def test_manifest_entry_point_and_release_version(self):
        manifest = json.loads(ROOT.joinpath("manifest.json").read_text())
        cargo = tomllib.loads(ROOT.joinpath("Cargo.toml").read_text())
        self.assertEqual(manifest["schemaVersion"], 1)
        self.assertEqual(manifest["version"], cargo["package"]["version"])
        self.assertEqual(manifest["license"], cargo["package"]["license"])
        self.assertEqual(manifest["id"], "gammamike.nudge")
        entry = Path(manifest["entryPoints"]["panel"])
        self.assertFalse(entry.is_absolute())
        self.assertNotIn("..", entry.parts)
        self.assertTrue(ROOT.joinpath(entry).is_file())


if __name__ == "__main__":
    unittest.main()
