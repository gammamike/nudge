import QtQuick
import QtTest
import Quickshell
import qs.Commons as Commons
import "Companion"

ShellRoot {
    Panel {
        id: panel
    }

    TestCase {
        name: "NudgeCompanion"
        when: true

        function settled() {
            tryCompare(panel, "busy", false, 4000);
        }

        function control(name) {
            var item = findChild(panel, name);
            verify(item !== null, "Missing control: " + name);
            return item;
        }

        function capture(name) {
            var captured = false;
            // grabToImage captures an item, not the native window background.
            var surface = control("panelSurface");
            var backdrop = Qt.createQmlObject('import QtQuick; Rectangle { anchors.fill: parent; z: -1 }', surface);
            backdrop.color = control("nudgeWindow").color;
            wait(100);
            verify(surface.grabToImage(function (result) {
                captured = result.saveToFile(Quickshell.env("NUDGE_UI_OUTPUT") + "/" + name + ".png");
            }));
            tryVerify(function () {
                return captured;
            }, 3000);
            backdrop.destroy();
        }

        function test_settings_and_theme_changes() {
            panel.open("{}");
            settled();
            verify(panel.available, panel.notice);
            verify(!panel.failed, panel.notice);
            verify(control("nudgeWindow").visible);

            var provider = control("providerPicker");
            var model = control("modelInput");
            var endpoint = control("endpointInput");
            var save = control("saveSettings");
            var reload = control("reloadSettings");
            var window = control("nudgeWindow");
            var testConnection = control("testConnection");
            compare(panel.connectionState, "untested");

            // Signals exercise the actual controls' handlers and the async CLI.
            provider.changed("claude");
            model.text = "haiku";
            compare(panel.savedConfig.provider, null);
            testConnection.clicked();
            settled();
            compare(panel.connectionState, "failed", "Missing Claude CLI must not appear connected");
            compare(panel.savedConfig.provider, null, "Testing must not save choices");
            save.clicked();
            settled();
            verify(!panel.failed, panel.notice);
            compare(panel.savedConfig.provider, "claude");
            model.text = "unsaved-model";
            reload.clicked();
            settled();
            compare(model.text, "haiku");

            provider.changed("ollama");
            compare(panel.connectionState, "untested");
            verify(!testConnection.enabled, "A local model is required for a test");
            verify(!save.enabled, "A local model is required");
            control("findModels").clicked();
            settled();
            verify(!panel.failed, panel.notice);
            compare(panel.discoveredModels.length, 1);
            control("localModelPicker").changed("qwen3:0.6b");
            compare(model.text, "qwen3:0.6b");
            testConnection.clicked();
            settled();
            compare(panel.connectionState, "connected", panel.connectionMessage);
            compare(panel.savedConfig.provider, "claude", "Testing unsaved Ollama settings must not switch the saved provider");
            var testMessage = panel.connectionMessage;
            control("setupTab").clicked();
            verify(panel.setupVisible);
            control("settingsTab").clicked();
            verify(!panel.setupVisible);
            compare(panel.connectionState, "connected", "Switching tabs must preserve the result");
            compare(panel.connectionMessage, testMessage, "Tab switches must preserve the test timestamp");
            save.clicked();
            settled();
            compare(panel.savedConfig.provider, "ollama");
            compare(panel.connectionState, "connected", "Saving tested choices must preserve the result");
            compare(panel.connectionMessage, testMessage);
            reload.clicked();
            settled();
            compare(panel.connectionState, "connected", "Reloading unchanged choices must preserve the result");
            compare(panel.connectionMessage, testMessage);
            // The CLI trims entered fields before use. Saving that same
            // normalized text must preserve the original result and time.
            model.text = " qwen3:0.6b ";
            compare(panel.connectionState, "connected", "Whitespace does not change the tested model");
            save.clicked();
            settled();
            compare(model.text, "qwen3:0.6b");
            compare(panel.connectionState, "connected");
            endpoint.text = " ";
            compare(panel.connectionState, "connected", "Whitespace keeps the blank endpoint choice");
            save.clicked();
            settled();
            compare(panel.connectionState, "connected", "Trimming saved fields must not invalidate the result");
            testConnection.clicked();
            model.text = "another-model";
            settled();
            compare(panel.connectionState, "untested", "Model edits invalidate the result");
            model.text = "qwen3:0.6b";
            verify(save.enabled);
            save.clicked();
            settled();
            compare(panel.savedConfig.provider, "ollama");

            endpoint.text = "https://example.com/v1";
            compare(panel.connectionState, "untested");
            testConnection.clicked();
            settled();
            compare(panel.connectionState, "failed");
            save.clicked();
            settled();
            verify(panel.failed, "Remote endpoints must fail");
            compare(endpoint.text, "https://example.com/v1", "Keep failed edits for repair");
            reload.clicked();
            settled();
            verify(!panel.failed, panel.notice);
            compare(panel.connectionState, "untested", "Reload clears the test result");

            // Use the same singleton update path as the host's theme IPC.
            Commons.Color.loadColors('background = "#101315"\nforeground = "#cacccc"\naccent = "#7aa2f7"\nred = "#f7768e"');
            Commons.Color.loadShell('[font]\nbase-size = 12');
            compare(window.color.toString(), "#101315");
            compare(model.color.toString(), "#cacccc");
            capture("settings-dark");

            Commons.Color.loadColors('background = "#ffffff"\nforeground = "#202020"\naccent = "#005f87"\nred = "#b02020"');
            Commons.Color.loadShell('[popups]\nbackground = "#f2efea"\ntext = "#242424"\n[font]\nbase-size = 16');
            compare(window.color.toString(), "#f2efea", "Honor popup palette overrides");
            compare(model.color.toString(), "#242424");
            compare(save.foreground.toString(), "#242424");
            compare(control("panelTitle").font.pixelSize, Commons.Style.font.display);
            compare(model.font.pixelSize, Commons.Style.font.body);
            window.implicitWidth = 560;
            capture("settings-light-large-type");

            control("setupTab").clicked();
            verify(panel.setupVisible);
            capture("setup-light");
            control("settingsTab").clicked();
            verify(!panel.setupVisible);
            panel.requestClose();
            verify(!window.visible);
            panel.open("{}");
            settled();
            verify(window.visible);
            compare(model.text, "qwen3:0.6b");
            panel.close();
            console.log("NUDGE_COMPANION_UI_PASS");
        }
    }
}
