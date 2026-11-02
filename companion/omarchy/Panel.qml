import QtQuick
import QtQuick.Controls as Controls
import Quickshell
import Quickshell.Io
import qs.Ui as Ui
import qs.Commons as Commons
import "Model.js" as Model

Item {
    id: root
    property var shell: null
    readonly property color foreground: Commons.Color.popups.text
    readonly property color background: Commons.Color.popups.background
    property bool closingFromHost: false
    property bool available: false
    property bool busy: false
    property bool setupVisible: false
    property string operation: ""
    property string notice: ""
    property bool failed: false
    property string binaryPath: ""
    property string configPath: ""
    property var savedConfig: ({})
    property var discoveredModels: []
    property string connectionState: "untested"
    property string connectionMessage: "Not tested"
    readonly property bool localProvider: Model.isLocal(provider.value)
    readonly property string helper: Model.localPath(Qt.resolvedUrl("bridge.sh").toString())

    function open(payloadJson) {
        closingFromHost = false;
        window.visible = true;
        if (!busy)
            run("status", []);
    }

    function close() {
        closingFromHost = true;
        window.visible = false;
        closingFromHost = false;
    }

    function requestClose() {
        if (shell && typeof shell.hide === "function")
            shell.hide("gammamike.nudge");
        else
            close();
    }

    function selectProvider(value) {
        resetConnection();
        provider.value = value;
        var fields = Model.fields(savedConfig, value);
        model.text = fields.model;
        endpoint.text = fields.endpoint;
        discoveredModels = [];
        notice = "";
    }

    function resetConnection() {
        connectionState = "untested";
        connectionMessage = "Not tested";
    }

    function run(action, args) {
        if (busy)
            return;
        busy = true;
        failed = false;
        notice = action === "save" ? "Saving…" : "Loading…";
        if (action === "test") {
            connectionState = "testing";
            connectionMessage = "Testing connection…";
            notice = "";
        }
        operation = action;
        process.command = ["/bin/bash", helper, action].concat(args);
        process.running = true;
    }

    function complete(exitCode, output, error) {
        busy = false;
        if (exitCode !== 0) {
            failed = true;
            notice = exitCode === 124 || exitCode === 137 ? "Nudge took too long to respond. Check the installation or local server and retry." : (error.trim().slice(0, 1200) || "Nudge could not complete this request.");
            if (operation === "test") {
                connectionState = "failed";
                connectionMessage = "Test failed: " + notice;
                notice = "";
            }
            return;
        }
        try {
            var result = JSON.parse(output);
            if (operation === "test") {
                if (typeof result.ok !== "boolean" || typeof result.message !== "string" || typeof result.model !== "string" || result.provider !== provider.value)
                    throw new Error("Invalid connection test response");
                connectionState = result.ok ? "connected" : "failed";
                connectionMessage = result.ok ? "Connected — " + result.model + " · tested " + new Date().toLocaleTimeString() : "Test failed: " + result.message;
                return;
            }
            if (operation === "models") {
                discoveredModels = Model.modelChoices(result.models);
                notice = discoveredModels.length ? "Choose a discovered model or enter an ID below." : "No local models found. Load a model on your server, then refresh.";
                return;
            }
            available = result.available === true;
            if (available) {
                binaryPath = result.binary;
                configPath = result.settings.path;
                savedConfig = result.settings.config;
                selectProvider(savedConfig.provider || "codex");
                notice = operation === "save" ? "Settings saved. Nudge reads them on its next request." : "Installed · ready to configure";
            } else {
                setupVisible = true;
                notice = "Install Nudge to configure it, then select Reload.";
            }
        } catch (e) {
            failed = true;
            notice = "Could not read Nudge's response. Update Nudge and try again.";
            if (operation === "test") {
                connectionState = "failed";
                connectionMessage = "Test failed: " + notice;
                notice = "";
            }
        }
    }

    Process {
        id: process
        stdout: StdioCollector {
            id: output
            waitForEnd: true
        }
        stderr: StdioCollector {
            id: errors
            waitForEnd: true
        }
        onExited: function (exitCode) {
            root.complete(exitCode, output.text, errors.text);
        }
    }

    component BodyText: Text {
        width: parent.width
        textFormat: Text.PlainText
        wrapMode: Text.Wrap
        color: root.foreground
        font.family: Commons.Style.font.family
        font.pixelSize: Commons.Style.font.body
    }

    component Action: Ui.Button {
        focusable: true
        bordered: true
        foreground: root.foreground
        opacity: enabled ? 1 : 0.45
    }

    component CommandBox: Column {
        property alias text: commandText.text
        width: parent.width
        spacing: Commons.Style.space(6)
        Controls.TextArea {
            id: commandText
            width: parent.width
            readOnly: true
            selectByMouse: true
            wrapMode: TextEdit.Wrap
            textFormat: TextEdit.PlainText
            color: root.foreground
            selectionColor: Commons.Style.selectionFillFor(root.foreground, Commons.Color.accent)
            selectedTextColor: root.foreground
            font.family: Commons.Style.font.family
            font.pixelSize: Commons.Style.font.body
            background: Ui.BorderSurface {
                color: "transparent"
                borderSpec: Commons.Border.controlSpec(commandText.activeFocus ? "focus" : "normal", root.foreground, Commons.Color.accent)
                radius: Commons.Style.cornerRadius
            }
        }
        Action {
            text: "Copy commands"
            onClicked: Quickshell.clipboardText = commandText.text
        }
    }

    FloatingWindow {
        id: window
        objectName: "nudgeWindow"
        visible: false
        title: "Nudge settings"
        color: root.background
        implicitWidth: 700
        implicitHeight: 780
        minimumSize: Qt.size(480, 400)
        onVisibleChanged: {
            if (!visible && !root.closingFromHost && root.shell && typeof root.shell.hide === "function")
                root.shell.hide("gammamike.nudge");
        }

        FocusScope {
            objectName: "panelSurface"
            anchors.fill: parent
            focus: true
            Keys.onEscapePressed: root.requestClose()

            Controls.ScrollView {
                id: scroll
                anchors.fill: parent
                anchors.margins: Commons.Style.space(24)
                clip: true
                Controls.ScrollBar.vertical: Controls.ScrollBar {
                    contentItem: Rectangle {
                        implicitWidth: Commons.Style.space(5)
                        implicitHeight: Commons.Style.space(30)
                        color: root.foreground
                        opacity: parent.pressed ? 0.8 : 0.4
                        radius: Commons.Style.cornerRadius
                    }
                }
                Controls.ScrollBar.horizontal.policy: Controls.ScrollBar.AlwaysOff

                Column {
                    width: scroll.availableWidth
                    spacing: Commons.Style.space(16)

                    BodyText {
                        text: "Nudge"
                        objectName: "panelTitle"
                        font.pixelSize: Commons.Style.font.display
                        font.bold: true
                    }
                    BodyText {
                        text: "Command correction for Linux and Bash"
                    }
                    Flow {
                        width: parent.width
                        spacing: Commons.Style.space(10)
                        Action {
                            text: "Settings"
                            objectName: "settingsTab"
                            selected: !root.setupVisible
                            onClicked: root.setupVisible = false
                        }
                        Action {
                            text: "Setup"
                            objectName: "setupTab"
                            selected: root.setupVisible
                            onClicked: root.setupVisible = true
                        }
                        Action {
                            text: "Close"
                            onClicked: root.requestClose()
                        }
                    }
                    BodyText {
                        text: root.notice
                        color: root.failed ? Commons.Color.urgent : root.foreground
                        visible: text !== ""
                        Accessible.role: Accessible.StaticText
                        Accessible.name: text
                    }

                    Column {
                        width: parent.width
                        spacing: Commons.Style.space(16)
                        visible: !root.setupVisible
                        BodyText {
                            text: "Local rules run first. The selected provider is an optional fallback for unresolved commands."
                        }
                        Ui.Dropdown {
                            id: provider
                            objectName: "providerPicker"
                            width: parent.width
                            label: "Fallback provider"
                            value: "codex"
                            options: Model.providers
                            enabled: root.available && !root.busy
                            onChanged: function (value) {
                                root.selectProvider(value);
                            }
                        }
                        BodyText {
                            text: root.localProvider ? "Start a local inference server and load a model. Only loopback HTTP endpoints are supported." : "Install and sign in to the selected provider's CLI in a terminal. Use a model ID or alias available to your account."
                        }
                        Column {
                            width: parent.width
                            spacing: Commons.Style.space(8)
                            visible: root.localProvider
                            BodyText {
                                text: "Server endpoint"
                            }
                            Ui.TextField {
                                id: endpoint
                                foreground: root.foreground
                                objectName: "endpointInput"
                                onTextChanged: root.resetConnection()
                                width: parent.width
                                enabled: root.available && !root.busy
                                placeholderText: Model.endpointHint(provider.value)
                                Accessible.name: "Server endpoint"
                                onTextEdited: root.discoveredModels = []
                            }
                            Action {
                                text: "Find local models"
                                objectName: "findModels"
                                enabled: root.available && !root.busy
                                onClicked: root.run("models", [provider.value, endpoint.text.trim()])
                            }
                            Ui.Dropdown {
                                width: parent.width
                                objectName: "localModelPicker"
                                label: "Available local models"
                                visible: root.discoveredModels.length > 0
                                options: root.discoveredModels
                                value: model.text
                                enabled: !root.busy
                                onChanged: function (value) {
                                    model.text = value;
                                }
                            }
                        }
                        Column {
                            width: parent.width
                            spacing: Commons.Style.space(8)
                            BodyText {
                                text: "Model ID or alias"
                            }
                            Ui.TextField {
                                id: model
                                foreground: root.foreground
                                objectName: "modelInput"
                                onTextChanged: root.resetConnection()
                                width: parent.width
                                enabled: root.available && !root.busy
                                placeholderText: root.localProvider ? "Choose or enter an installed model" : "Keep saved model or provider default"
                                Accessible.name: "Model ID or alias"
                            }
                            BodyText {
                                text: "Blank fields keep saved values or Nudge's defaults. Local inference requires a model. Exported NUDGE_* variables in your terminal override saved choices."
                            }
                        }
                        Column {
                            width: parent.width
                            spacing: Commons.Style.space(8)
                            BodyText {
                                objectName: "connectionStatus"
                                text: root.connectionMessage
                                color: root.connectionState === "failed" ? Commons.Color.urgent : root.foreground
                                Accessible.role: Accessible.StaticText
                                Accessible.name: text
                            }
                            Action {
                                text: root.connectionState === "testing" ? "Testing…" : "Test connection"
                                objectName: "testConnection"
                                enabled: root.available && !root.busy && (!root.localProvider || model.text.trim() !== "")
                                onClicked: root.run("test", [provider.value, model.text.trim(), root.localProvider ? endpoint.text.trim() : ""])
                            }
                            BodyText {
                                text: "Sends one small test request using these choices, without saving. Uses provider allowance or local compute; no shell history is sent. Results describe this test, not continuous monitoring."
                                font.pixelSize: Commons.Style.font.caption
                            }
                        }
                        Flow {
                            width: parent.width
                            spacing: Commons.Style.space(10)
                            Action {
                                text: "Save settings"
                                objectName: "saveSettings"
                                enabled: root.available && !root.busy && (!root.localProvider || model.text.trim() !== "")
                                onClicked: root.run("save", [provider.value, model.text.trim(), root.localProvider ? endpoint.text.trim() : ""])
                            }
                            Action {
                                text: "Reload"
                                objectName: "reloadSettings"
                                enabled: !root.busy
                                onClicked: root.run("status", [])
                            }
                        }
                        BodyText {
                            visible: root.available
                            text: "Configuration: " + root.configPath + "\nCLI: " + root.binaryPath
                            font.pixelSize: Commons.Style.font.caption
                        }
                    }

                    Column {
                        width: parent.width
                        spacing: Commons.Style.space(16)
                        visible: root.setupVisible
                        BodyText {
                            text: "1. Install Nudge"
                            font.bold: true
                        }
                        BodyText {
                            text: "The companion configures Nudge; install the CLI separately. From source, you need Git, Bash 5+, and Rust 1.88+ with Cargo. Run these commands in a terminal:"
                        }
                        CommandBox {
                            text: "git clone https://github.com/gammamike/nudge.git\ncd nudge\n./install.sh\nexec bash"
                        }
                        BodyText {
                            text: "The per-user installer backs up ~/.bashrc and enables the hook. Remove an earlier manual Nudge source line before installing. Start a new Bash shell after installation or updates."
                        }
                        BodyText {
                            text: "2. Enable the Bash hook"
                            font.bold: true
                        }
                        BodyText {
                            text: "If you used ./install.sh, this is already done. For a system package installed under /usr, add the following line once to ~/.bashrc, then open a new terminal. Change the prefix for a manual installation elsewhere."
                        }
                        CommandBox {
                            text: "[[ -r /usr/lib/nudge-bash/nudge.bash ]] && source /usr/lib/nudge-bash/nudge.bash"
                        }
                        BodyText {
                            text: "Verify in the new terminal with: declare -p _NUDGE_LOADED (expect 1). This desktop panel cannot inspect a terminal's hook state. To use only local rules, add export NUDGE_LOCAL_ONLY=1 to ~/.bashrc."
                        }
                        BodyText {
                            text: "3. Choose an optional provider"
                            font.bold: true
                        }
                        BodyText {
                            text: "Codex and Claude Code use their existing subscription CLI login. For a local LLM, start Ollama or a compatible loopback server; local model discovery also needs curl. Then open Settings, choose a provider and model, and save."
                        }
                        Action {
                            text: "Reload installation"
                            enabled: !root.busy
                            onClicked: root.run("status", [])
                        }
                        Action {
                            text: "Installation and provider documentation"
                            onClicked: Qt.openUrlExternally("https://github.com/gammamike/nudge/blob/main/docs/OMARCHY_COMPANION.md")
                        }
                    }
                }
            }
        }
    }
}
