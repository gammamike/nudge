import QtQuick
import Quickshell.Io
import "Model.js" as Model

Item {
    id: root
    property var shell: null
    property bool checked: false
    onShellChanged: {
        if (shell && !checked)
            startup.start();
    }

    Timer {
        id: startup
        interval: 500
        onTriggered: {
            root.checked = true;
            check.running = true;
        }
    }

    Process {
        id: check
        command: ["/bin/bash", Model.localPath(Qt.resolvedUrl("welcome.sh").toString()), "status"]
        stdout: StdioCollector { id: output; waitForEnd: true }
        stderr: StdioCollector { waitForEnd: true }
        onExited: function (exitCode) {
            if (exitCode !== 0 || !root.shell)
                return;
            try {
                var result = JSON.parse(output.text);
                if (result.seen === false && !root.shell.isPluginOpen("gammamike.nudge"))
                    root.shell.summon("gammamike.nudge", '{"welcome":true}');
            } catch (e) {
                console.warn("Nudge could not check first-run setup status: " + e);
            }
        }
    }
}
