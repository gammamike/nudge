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

        function expect(condition, message) {
            if (!condition)
                console.error("UI assertion failed: " + message);
            verify(condition, message);
        }

        function expectEqual(actual, expected, message) {
            if (actual !== expected)
                console.error("UI comparison failed: " + actual + " != " + expected + " " + (message || ""));
            compare(actual, expected, message);
        }

        function settled() {
            tryCompare(panel, "busy", false, 4000);
        }

        function control(name) {
            var item = findChild(panel, name);
            expect(item !== null, "Missing control: " + name);
            return item;
        }

        function capture(name) {
            var captured = false;
            // grabToImage captures an item, not the native window background.
            var surface = control("panelSurface");
            var backdrop = Qt.createQmlObject('import QtQuick; Rectangle { anchors.fill: parent; z: -1 }', surface);
            backdrop.color = control("nudgeWindow").color;
            wait(100);
            expect(surface.grabToImage(function (result) {
                captured = result.saveToFile(Quickshell.env("NUDGE_UI_OUTPUT") + "/" + name + ".png");
            }));
            tryVerify(function () {
                return captured;
            }, 3000);
            backdrop.destroy();
        }

        Component {
            id: welcomeComponent
            Welcome {}
        }
        QtObject {
            id: host
            property int summons: 0
            function isPluginOpen(id) { return false; }
            function summon(id, payload) {
                summons++;
                panel.open(payload);
                return true;
            }
        }

        function test_00_welcome_once() {
            var service = welcomeComponent.createObject(null, {shell: host});
            tryCompare(host, "summons", 1, 4000);
            console.log("WELCOME summoned");
            settled();
            console.log("WELCOME settled");
            expect(panel.setupVisible, "First enable must explain setup");
            expect(control("nudgeWindow").visible);
            wait(100);
            panel.close();
            service.destroy();
            service = welcomeComponent.createObject(null, {shell: host});
            wait(900);
            expectEqual(host.summons, 1, "Shell reload must not repeat the welcome");
            expect(!control("nudgeWindow").visible);
            service.destroy();
            console.log("WELCOME checks passed");
            panel.setupVisible = false;
        }

        function test_settings_and_theme_changes() {
            panel.open("{}");
            settled();
            expect(panel.available, panel.notice);
            expect(!panel.failed, panel.notice);
            expect(control("nudgeWindow").visible);

            var provider = control("providerPicker");
            var model = control("modelInput");
            var endpoint = control("endpointInput");
            var save = control("saveSettings");
            var reload = control("reloadSettings");
            var window = control("nudgeWindow");
            var testConnection = control("testConnection");
            expectEqual(panel.connectionState, "untested");

            // Signals exercise the actual controls' handlers and the async CLI.
            provider.changed("claude");
            model.text = "haiku";
            expectEqual(panel.savedConfig.provider, null);
            testConnection.clicked();
            settled();
            expectEqual(panel.connectionState, "failed", "Missing Claude CLI must not appear connected");
            expectEqual(panel.savedConfig.provider, null, "Testing must not save choices");
            save.clicked();
            settled();
            expect(!panel.failed, panel.notice);
            expectEqual(panel.savedConfig.provider, "claude");
            model.text = "unsaved-model";
            reload.clicked();
            settled();
            expectEqual(model.text, "haiku");

            provider.changed("ollama");
            expectEqual(panel.connectionState, "untested");
            expect(!testConnection.enabled, "A local model is required for a test");
            expect(!save.enabled, "A local model is required");
            control("findModels").clicked();
            settled();
            expect(!panel.failed, panel.notice);
            expectEqual(panel.discoveredModels.length, 1);
            control("localModelPicker").changed("qwen3:0.6b");
            expectEqual(model.text, "qwen3:0.6b");
            testConnection.clicked();
            settled();
            expectEqual(panel.connectionState, "connected", panel.connectionMessage);
            expectEqual(panel.savedConfig.provider, "claude", "Testing unsaved Ollama settings must not switch the saved provider");
            var testMessage = panel.connectionMessage;
            control("setupTab").clicked();
            expect(panel.setupVisible);
            expect(!panel.launcherInstalled);
            control("installNudge").clicked();
            settled();
            expect(panel.launcherInstalled, panel.notice);
            expectEqual(panel.connectionState, "connected");
            expect(!control("installLauncher").enabled);
            expect(control("removeLauncher").enabled);
            control("settingsTab").clicked();
            expect(!panel.setupVisible);
            expectEqual(panel.connectionState, "connected", "Switching tabs must preserve the result");
            expectEqual(panel.connectionMessage, testMessage, "Tab switches must preserve the test timestamp");
            save.clicked();
            settled();
            expectEqual(panel.savedConfig.provider, "ollama");
            expectEqual(panel.connectionState, "connected", "Saving tested choices must preserve the result");
            expectEqual(panel.connectionMessage, testMessage);
            expect(panel.launcherInstalled, "Reload must preserve launcher status");
            reload.clicked();
            settled();
            expectEqual(panel.connectionState, "connected", "Reloading unchanged choices must preserve the result");
            expectEqual(panel.connectionMessage, testMessage);
            // The CLI trims entered fields before use. Saving that same
            // normalized text must preserve the original result and time.
            model.text = " qwen3:0.6b ";
            expectEqual(panel.connectionState, "connected", "Whitespace does not change the tested model");
            save.clicked();
            settled();
            expectEqual(model.text, "qwen3:0.6b");
            expectEqual(panel.connectionState, "connected");
            endpoint.text = " ";
            expectEqual(panel.connectionState, "connected", "Whitespace keeps the blank endpoint choice");
            save.clicked();
            settled();
            expectEqual(panel.connectionState, "connected", "Trimming saved fields must not invalidate the result");
            testConnection.clicked();
            model.text = "another-model";
            settled();
            expectEqual(panel.connectionState, "untested", "Model edits invalidate the result");
            model.text = "qwen3:0.6b";
            expect(save.enabled);
            save.clicked();
            settled();
            expectEqual(panel.savedConfig.provider, "ollama");

            endpoint.text = "https://example.com/v1";
            expectEqual(panel.connectionState, "untested");
            testConnection.clicked();
            settled();
            expectEqual(panel.connectionState, "failed");
            save.clicked();
            settled();
            expect(panel.failed, "Remote endpoints must fail");
            expectEqual(endpoint.text, "https://example.com/v1", "Keep failed edits for repair");
            reload.clicked();
            settled();
            expect(!panel.failed, panel.notice);
            expectEqual(panel.connectionState, "untested", "Reload clears the test result");

            // Use the same singleton update path as the host's theme IPC.
            Commons.Color.loadColors('background = "#101315"\nforeground = "#cacccc"\naccent = "#7aa2f7"\nred = "#f7768e"');
            Commons.Color.loadShell('[font]\nbase-size = 12');
            expectEqual(window.color.toString(), "#101315");
            expectEqual(model.color.toString(), "#cacccc");
            var scroll = control("panelScrollView");
            var scrollbar = control("panelScrollBar");
            wait(100);
            expect(scrollbar.size >= 1, "Default-size text should fit in the window");
            expect(!scrollbar.contentItem.visible || scrollbar.contentItem.opacity === 0,
                   "A scrollbar thumb must not appear when all content fits");
            Commons.Color.loadShell('[font]\nbase-size = 16');
            wait(100);
            expect(scrollbar.size < 1, "Larger text must remain scrollable");
            var scrollbarOrigin = scrollbar.mapToItem(scroll, 0, 0);
            expect(scrollbarOrigin.x >= scroll.width - scrollbar.width - 1,
                   "The vertical scrollbar must stay at the right edge, away from the title");
            expectEqual(Math.round(scrollbar.height), Math.round(scroll.availableHeight));
            expect(scrollbar.contentItem.visible && scrollbar.contentItem.opacity > 0);
            Commons.Color.loadShell('[font]\nbase-size = 12');
            wait(100);
            capture("settings-dark");

            Commons.Color.loadColors('background = "#ffffff"\nforeground = "#202020"\naccent = "#005f87"\nred = "#b02020"');
            Commons.Color.loadShell('[popups]\nbackground = "#f2efea"\ntext = "#242424"\n[font]\nbase-size = 16');
            expectEqual(window.color.toString(), "#f2efea", "Honor popup palette overrides");
            expectEqual(model.color.toString(), "#242424");
            expectEqual(save.foreground.toString(), "#242424");
            expectEqual(control("panelTitle").font.pixelSize, Commons.Style.font.display);
            expectEqual(model.font.pixelSize, Commons.Style.font.body);
            window.implicitWidth = 560;
            capture("settings-light-large-type");

            control("setupTab").clicked();
            expect(panel.setupVisible);
            control("removeLauncher").clicked();
            settled();
            expect(!panel.launcherInstalled, panel.notice);
            capture("setup-light");
            control("settingsTab").clicked();
            expect(!panel.setupVisible);
            panel.requestClose();
            expect(!window.visible);
            panel.open("{}");
            settled();
            expect(window.visible);
            expectEqual(model.text, "qwen3:0.6b");
            panel.close();
            console.log("NUDGE_COMPANION_UI_PASS");
        }
    }
}
