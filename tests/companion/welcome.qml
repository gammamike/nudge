import QtQuick
import QtTest
import Quickshell
import qs.Commons as Commons
import "Companion"

ShellRoot {
    Panel { id: panel }
    TestCase {
        when: true
        function capture(name) {
            var surface = findChild(panel, "panelSurface");
            var backdrop = Qt.createQmlObject('import QtQuick; Rectangle { anchors.fill: parent; z: -1 }', surface);
            backdrop.color = findChild(panel, "nudgeWindow").color;
            var saved = false;
            wait(150);
            verify(surface.grabToImage(function (result) {
                saved = result.saveToFile(Quickshell.env("NUDGE_UI_OUTPUT") + "/" + name + ".png");
            }));
            tryVerify(function () { return saved; }, 3000);
            backdrop.destroy();
        }
        function test_welcome_preview() {
            Commons.Color.loadColors('background = "#101315"\nforeground = "#cacccc"\naccent = "#7aa2f7"\nred = "#f7768e"');
            Commons.Color.loadShell('[font]\nbase-size = 14');
            var window = findChild(panel, "nudgeWindow");
            window.implicitWidth = 800;
            window.implicitHeight = 1140;
            panel.open('{"welcome":true}');
            tryCompare(panel, "busy", false, 4000);
            verify(!panel.available, "Preview must represent a fresh install");
            verify(panel.setupVisible);
            capture("welcome-dark");
            Commons.Color.loadColors('background = "#f2efea"\nforeground = "#242424"\naccent = "#005f87"\nred = "#b02020"');
            capture("welcome-light");
            panel.close();
            console.log("NUDGE_COMPANION_UI_PASS");
        }
    }
}
