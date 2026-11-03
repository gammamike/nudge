# Preview sources

`command-correction.svg` typesets output captured from a real Bash session with
Nudge's local rules and `git statsu`. The suggestion was cancelled. The recorded
12 ms is one example, not a performance guarantee. Regenerate the marketplace
preview with `rsvg-convert docs/images/command-correction.svg -o preview.png`.

The panel PNGs are captures of the real QML controls, with disposable settings.
Generate welcome screenshots using:

```bash
python3 tests/companion_ui_smoke.py --welcome-only --output /tmp/nudge-welcome
```

Generate settings screenshots and run panel regressions using:

```bash
python3 tests/companion_ui_smoke.py --output /tmp/nudge-panel
```

Review the captures before copying them here. These commands do not change the
running desktop theme, install the companion, or contact a model provider.
