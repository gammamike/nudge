#!/usr/bin/env python3
"""Run the real Omarchy QML components offscreen, with isolated settings."""
import argparse
from pathlib import Path
import shutil
import subprocess
import tempfile

from support import BINARY, ROOT


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True,
                        help="Directory for dark/light screenshots")
    parser.add_argument("--omarchy", type=Path, default=Path("/usr/share/omarchy"))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    quickshell = shutil.which("quickshell")
    if not quickshell or not args.omarchy.joinpath("shell/Ui").is_dir():
        parser.error("Install Omarchy Shell and Quickshell to run this optional check")
    with tempfile.TemporaryDirectory(prefix="nudge companion ui-") as temporary:
        root = Path(temporary)
        for name in ("Ui", "Commons"):
            root.joinpath(name).symlink_to(args.omarchy / "shell" / name,
                                         target_is_directory=True)
        shutil.copytree(ROOT / "companion/omarchy", root / "Companion")
        shutil.copyfile(ROOT / "tests/companion/shell.qml", root / "shell.qml")
        home = root / "home"
        fontconfig = home / ".config/fontconfig/fonts.conf"
        fontconfig.parent.mkdir(parents=True)
        fontconfig.write_text('''<?xml version="1.0"?>
<!DOCTYPE fontconfig SYSTEM "urn:fontconfig:fonts.dtd">
<fontconfig><alias><family>monospace</family><prefer><family>JetBrainsMono Nerd Font</family></prefer></alias></fontconfig>
''')
        bin_dir = home / "bin"
        bin_dir.mkdir(parents=True)
        bin_dir.joinpath("nudge-bash").symlink_to(BINARY)
        # Allow the bridge's dependencies, but no provider CLI or live curl.
        for name in ("jq", "timeout", "fc-match"):
            bin_dir.joinpath(name).symlink_to(shutil.which(name))
        curl = bin_dir / "curl"
        curl.write_text('''#!/bin/bash
case "$*" in
  */api/show*) printf '%s\\n' '{"model_info":{}}' ;;
  */api/chat*) printf '%s\\n' '{"done":true,"done_reason":"stop","message":{"role":"assistant","content":"{\\"candidate_id\\":0}"}}' ;;
  *) printf '%s\\n' '{"models":[{"name":"qwen3:0.6b"}]}' ;;
esac
''')
        curl.chmod(0o700)
        hyprctl = bin_dir / "hyprctl"
        hyprctl.write_text('#!/bin/bash\nprintf \'{"int":4}\\n\'\n')
        hyprctl.chmod(0o700)
        runtime = root / "runtime"
        runtime.mkdir(mode=0o700)
        env = {
            "HOME": str(home), "PATH": str(bin_dir), "LC_ALL": "C.UTF-8",
            "XDG_CONFIG_HOME": str(home / ".config"),
            "XDG_DATA_HOME": str(home / ".local/share"),
            "XDG_CACHE_HOME": str(home / ".cache"),
            "XDG_RUNTIME_DIR": str(runtime),
            "QT_QPA_PLATFORM": "offscreen", "QT_QPA_PLATFORMTHEME": "generic",
            "QT_QUICK_CONTROLS_STYLE": "Basic", "QT_QUICK_BACKEND": "software",
            "NUDGE_UI_OUTPUT": str(args.output.resolve()),
            "NO_COLOR": "1",
        }
        result = subprocess.run([quickshell, "--path", str(root), "--no-duplicate"],
                                env=env, capture_output=True, text=True, timeout=30)
        output = result.stdout + result.stderr
        print(output, end="")
        if result.returncode or "NUDGE_COMPANION_UI_PASS" not in output:
            raise SystemExit("Companion UI checks failed")
        for name in ("settings-dark", "settings-light-large-type", "setup-light"):
            if not args.output.joinpath(name + ".png").is_file():
                raise SystemExit(f"Missing screenshot: {name}")
        print(f"UI checks passed; screenshots: {args.output.resolve()}")


if __name__ == "__main__":
    main()
