# Optional Omarchy companion

Nudge works on Linux with interactive Bash 5+, independently of a desktop.
The optional Omarchy companion provides a settings window for **Codex, Claude
Code, and local LLMs**, plus installation and Bash activation instructions.
It uses the Omarchy Shell plugin interface tested with Omarchy 4.0.6-1.
Older installations without `omarchy plugin` and `omarchy-shell` are not supported.

The panel follows the active Omarchy theme through the shell's shared controls
and theme state. Popup colors, text, accents, borders, spacing, and font sizes
update with theme changes, including `shell.toml` overrides. The font family
follows Omarchy's system monospace selection.

The companion and CLI share this repository and version. The root
`manifest.json` identifies `gammamike.nudge`; its entry point is
`companion/omarchy/Panel.qml`. No fork or separate runtime is needed.

## Install the companion

The companion is not yet published in the marketplace. After the companion
is merged and available on the repository's default branch:

```bash
omarchy plugin add https://github.com/gammamike/nudge.git --enable
omarchy-shell shell summon gammamike.nudge '{}'
```

This adds a standalone settings panel, not a replacement bar. Installing the
companion does not build or install Nudge, authenticate a provider, or edit
`~/.bashrc`. The Setup tab explains those separate steps.

For local development before publication, copy the companion into a new user
plugin directory. Run from the repository root; the destination must not exist:

```bash
plugin_dir="$HOME/.config/omarchy/plugins/gammamike.nudge"
mkdir -p "$(dirname "$plugin_dir")"
mkdir "$plugin_dir" && cp -R manifest.json companion "$plugin_dir/"
omarchy plugin validate "$plugin_dir"
omarchy-shell shell rescanPlugins
omarchy plugin enable gammamike.nudge
omarchy-shell shell summon gammamike.nudge '{}'
```

Stop if `mkdir` reports that the destination exists; inspect or back up that
installation before replacing it. Do not copy `target/`, `dist/`, or personal
configuration. Omarchy rejects symlinks in plugin packages. Never edit the
plugins shipped under `/usr/share/omarchy`.

Omarchy reloads plugins asynchronously when their files change. If the first
open is interrupted by that reload, run the `summon` command again after the
reload completes. A shell restart is not required.

## Install Nudge and activate Bash

Use one installation method. From source, with Git, Rust 1.88+, and Cargo:

```bash
git clone https://github.com/gammamike/nudge.git
cd nudge
./install.sh
exec bash
```

The installer backs up `~/.bashrc` and adds one managed hook block. Remove any
earlier manual Nudge source line before installing; do not add another hook
after using the installer. With `--no-modify-shell`, follow the manual activation
instructions in [installation](INSTALLATION.md).

For a package installed under `/usr`, add this line once to `~/.bashrc`:

```bash
[[ -r /usr/lib/nudge-bash/nudge.bash ]] && source /usr/lib/nudge-bash/nudge.bash
```

Adjust the prefix for other Makefile installations. Open a new Bash terminal
and run `declare -p _NUDGE_LOADED`; the value should be `1`. The desktop panel
cannot inspect hooks in existing terminal processes. See
[system installation](SYSTEM_INSTALL.md) for package setup and removal.
AUR packages and public release downloads have not been published yet.

## Choose a provider and model

1. Open the panel and select **Settings**.
2. Select Codex, Claude Code, Ollama, or a compatible local server.
3. Enter a model ID or alias available to your account or installed locally.
   For local servers, enter a loopback HTTP endpoint and select **Find local
   models** to populate the model picker. You can also type the ID directly.
4. Optionally select **Test connection**. This sends one small synthetic request
   through the selected provider and model, using provider allowance or local
   compute. It does not save settings or send shell history. The result shows
   **Connected** only after a usable model response, or a failure message.
5. Select **Save settings**. Changes apply on Nudge's next request. **Reload**
   discards unsaved edits and rereads the configuration.

Connection status starts at **Not tested**. Editing the provider, model, or
endpoint, or reloading settings, clears the previous result. A successful test
shows the tested model and time; it is not continuous monitoring. Testing is
explicit and still sends a request when terminal correction fallback is disabled
with `NUDGE_LOCAL_ONLY=1`. Opening the panel does not contact providers.

Changing the provider picker does not save anything. Blank fields preserve
saved values or Nudge's defaults; they do not remove existing overrides. The
panel edits saved settings, while exported `NUDGE_*` variables in each terminal
still take precedence. Use `nudge config` or `nudge-bash config` in that terminal
to inspect its effective settings. Local inference requires an explicit model.

Codex and Claude Code use their separately installed CLI's existing subscription
login. Choose a supported model through that CLI if unsure of its ID. Their
account-specific model lists are not enumerated by this panel. Local LLMs need
a separately running server and `curl`; defaults are
`http://127.0.0.1:11434` for Ollama and `http://127.0.0.1:1234/v1` for a compatible
server. See [provider configuration](PROVIDERS.md) for authentication,
environment overrides, and privacy boundaries.

To disable model fallback, add `export NUDGE_LOCAL_ONLY=1` to `~/.bashrc` and
start a fresh Bash shell. Deterministic corrections continue working.

## How settings are stored

The panel calls the installed Rust CLI through a small Bash adapter. It requires
`jq` and GNU `timeout`, normally available on Omarchy, and uses Nudge's normal
configuration file at `$XDG_CONFIG_HOME/nudge/config.json` (default
`~/.config/nudge/config.json`) or `NUDGE_CONFIG` if set in the desktop environment.
The CLI validates values and saves atomically with user-only permissions.

Discovery prefers `nudge-bash` on the desktop's PATH, then a managed per-user
installation under `$XDG_DATA_HOME/nudge/current`, then fixed package layouts
under `~/.local`, `/usr/local`, and `/usr`. It deliberately ignores a bare
`nudge` on PATH because other software uses that name. Custom package prefixes
must expose `nudge-bash` on the desktop PATH. Custom per-user `--prefix` layouts
are also not auto-discovered; expose that installed executable as `nudge-bash`
on the desktop PATH. Relative XDG directory values use the home-directory
default, matching the CLI. Select **Reload** after installation.

The panel does not read provider credentials or shell history, download models,
or execute proposed corrections. **Find local models** only queries the selected
loopback server. **Test connection** uses the CLI's existing subscription or
local-model boundaries and only fixed test data. Arguments are passed directly
to the CLI without shell evaluation. Ordinary invocations are limited to 15
seconds; connection tests allow 25 seconds including CLI authentication, with a
15-second model request budget. The CLI can be tested separately with
`nudge check-provider` or `nudge-bash check-provider`.

## Update and remove

For a Git-installed companion, use Omarchy's plugin update command:

```bash
omarchy plugin update gammamike.nudge
```

For a development copy, update the copied files from the same repository version;
Omarchy watches user plugin files. Update the CLI separately using the method
that installed it. No shell restart is needed for saved provider choices; a new
Bash shell is needed after updating hook code.

```bash
omarchy plugin remove gammamike.nudge
```

Removing the companion leaves Nudge, its Bash hook, and saved settings in place.
To remove Nudge itself, follow its per-user or package uninstall instructions.

## Validation

The normal integration suite exercises discovery, configuration of all four
providers, invalid input, local model listing, and failures in disposable home
directories. Model requests use mocks, not accounts or live inference.
On an Omarchy development machine, also validate the staged plugin with
`omarchy plugin validate`, open the panel, and check keyboard navigation,
provider changes, local model selection, Save/Reload, Setup, and window closure.
Run `bash -n companion/omarchy/bridge.sh` for the adapter's syntax check.

For a repeatable offscreen check on an Omarchy machine with QtTest installed:

```bash
python3 tests/companion_ui_smoke.py --output /tmp/nudge-companion-previews
```

This uses the installed Omarchy controls, a disposable home, the built Rust
binary, and a mocked local server. It tests settings changes, Save/Reload,
local model selection, error recovery, window closure, and live theme updates.
It renders dark and light screenshots, including larger text, for visual review.
It does not change the running desktop's theme, plugins, or settings.

A live installation check on Omarchy 4.0.6-1 also verified the managed CLI
installation, Bash hook activation in a fresh shell, companion discovery,
rendering with the active desktop theme, and close/reopen through the shell
host. The initial launch overlapped the plugin reload and required reopening;
subsequent close/reopen checks passed. Provider settings were preserved.
Separate disposable-home checks verified missing-CLI detection, source
installation, repeated installation without duplicate hooks, and uninstall.
