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
    property bool launcherInstalled: false
    property string operation: ""
    property string notice: ""
    property bool failed: false
    property string binaryPath: ""
    property string configPath: ""
    property var savedConfig: ({})
    property var discoveredModels: []
    property string connectionState: "untested"
    property string connectionMessage: "Not tested"
    property string testedConnectionKey: ""
    property bool loadingFields: false
    readonly property bool localProvider: Model.isLocal(provider.value)
    readonly property string helper: Model.localPath(Qt.resolvedUrl("bridge.sh").toString())

    function open(payloadJson) {
        closingFromHost = false;
        try {
            if (JSON.parse(payloadJson || "{}").welcome === true)
                setupVisible = true;
        } catch (e) {}
        window.visible = true;
        if (!welcomeMarker.running)
            welcomeMarker.running = true;
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
        // Compare the final form values, not intermediate text-change signals
        // emitted while saved settings are being loaded.
        loadingFields = true;
        provider.value = value;
        var fields = Model.fields(savedConfig, value);
        model.text = fields.model;
        endpoint.text = fields.endpoint;
        loadingFields = false;
        invalidateConnection();
        discoveredModels = [];
        notice = "";
    }

    function connectionKey() {
        return JSON.stringify([provider.value, model.text.trim(), root.localProvider ? endpoint.text.trim() : ""]);
    }

    function invalidateConnection() {
        if (!loadingFields && testedConnectionKey !== "" && connectionKey() !== testedConnectionKey)
            resetConnection();
    }

    function resetConnection() {
        testedConnectionKey = "";
        connectionState = "untested";
        connectionMessage = "Not tested";
    }

    function run(action, args) {
        if (busy)
            return;
        busy = true;
        failed = false;
        notice = action === "save" ? "Saving…" : "Loading…";
        if (action === "setup")
            notice = "Setting up Nudge… Downloads can take a few minutes. Keep this panel open.";
        if (action === "test") {
            testedConnectionKey = connectionKey();
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
        if (operation === "test" && connectionKey() !== testedConnectionKey) {
            resetConnection();
            return;
        }
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
            if (operation === "launcher-install" || operation === "launcher-remove") {
                if (typeof result.installed !== "boolean")
                    throw new Error("Invalid launcher response");
                launcherInstalled = result.installed;
                notice = launcherInstalled ? "Launcher added. Press Super+Space and search for Nudge Settings." : "Launcher shortcut removed.";
                return;
            }
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
            var preserveChoices = operation === "setup" && available;
            available = result.available === true;
            launcherInstalled = !!result.launcher && result.launcher.installed === true;
            if (available) {
                binaryPath = result.binary;
                configPath = result.settings.path;
                savedConfig = result.settings.config;
                if (!preserveChoices)
                    selectProvider(savedConfig.provider || "codex");
                notice = operation === "setup" ? "Setup complete. Open a new Bash terminal to start using Nudge. Press Super+Space to find Nudge Settings." : operation === "save" ? "Settings saved. Nudge reads them on its next request." : "CLI installed · open a new Bash terminal after setup";
            } else {
                resetConnection();
                setupVisible = true;
                notice = "Welcome to Nudge. Complete setup below to enable command corrections.";
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
        id: welcomeMarker
        command: ["/bin/bash", Model.localPath(Qt.resolvedUrl("welcome.sh").toString()), "mark"]
        stderr: StdioCollector { waitForEnd: true }
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
                objectName: "panelScrollView"
                anchors.fill: parent
                anchors.margins: Commons.Style.space(24)
                clip: true
                Controls.ScrollBar.vertical.objectName: "panelScrollBar"
                Controls.ScrollBar.vertical.contentItem: Rectangle {
                    implicitWidth: Commons.Style.space(5)
                    implicitHeight: Commons.Style.space(30)
                    visible: scroll.Controls.ScrollBar.vertical.size < 1
                    color: root.foreground
                    opacity: scroll.Controls.ScrollBar.vertical.pressed ? 0.8 : 0.4
                    radius: Commons.Style.cornerRadius
                }
                Controls.ScrollBar.horizontal.policy: Controls.ScrollBar.AlwaysOff

                Column {
                    width: scroll.availableWidth - Commons.Style.space(12)
                    spacing: Commons.Style.space(16)

                    BodyText {
                        text: "Nudge"
                        objectName: "panelTitle"
                        font.pixelSize: Commons.Style.font.display
                        font.bold: true
                    }
                    BodyText {
                        text: "Suggested autocorrect for Linux commands"
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
                                onTextChanged: root.invalidateConnection()
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
                                onTextChanged: root.invalidateConnection()
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
                            text: "Learn unfamiliar commands with fewer retries"
                            font.bold: true
                        }
                        BodyText {
                            text: "New tool? Forgotten subcommand? Nudge checks failed commands in Bash and suggests a correction. Enter runs it; any other key cancels. Keep working in your usual terminal."
                        }
                        BodyText {
                            text: "$ git statsu\n\n nudge [local]: git status\n Enter to run · Any other key to cancel"
                        }
                        BodyText {
                            text: "Install once, then open a new terminal"
                            font.bold: true
                        }
                        BodyText {
                            text: "Installs the Linux x86_64 CLI for your user, backs up ~/.bashrc and adds its Bash hook, and adds Nudge Settings to Super+Space. No administrator password or Rust toolchain needed. Existing settings are preserved."
                        }
                        BodyText {
                            text: "Local rules run first. Unresolved eligible commands use Codex cloud fallback by default; Claude Code and local LLMs are alternatives. Model requests happen before Enter-to-run confirmation. Setup does not contact a model."
                        }
                        Action {
                            text: root.busy && root.operation === "setup" ? "Setting up…" : root.available ? "Complete Bash & launcher setup" : "Install Nudge & enable Bash"
                            objectName: "installNudge"
                            enabled: !root.busy
                            onClicked: root.run("setup", [])
                        }
                        BodyText {
                            text: "For local rules only, add export NUDGE_LOCAL_ONLY=1 to ~/.bashrc before opening the new terminal. Package/custom installations and other architectures: use the installation guide below."
                            font.pixelSize: Commons.Style.font.caption
                        }
                        BodyText {
                            text: "Provider and model"
                            font.bold: true
                        }
                        BodyText {
                            text: "Choose Codex, Claude Code, or a local LLM in Settings. Cloud providers use their separately installed CLI login. Local models need a running Ollama or compatible loopback server. Test connection checks your selection."
                        }
                        BodyText {
                            text: "Launcher shortcut"
                            font.bold: true
                        }
                        BodyText {
                            text: "Included in guided setup. Add or remove it separately here. Remove it before uninstalling the companion."
                        }
                        Flow {
                            width: parent.width
                            spacing: Commons.Style.space(10)
                            Action {
                                text: root.launcherInstalled ? "Launcher added" : "Add launcher shortcut"
                                objectName: "installLauncher"
                                enabled: !root.busy && !root.launcherInstalled
                                onClicked: root.run("launcher-install", [])
                            }
                            Action {
                                text: "Remove launcher shortcut"
                                objectName: "removeLauncher"
                                enabled: !root.busy && root.launcherInstalled
                                onClicked: root.run("launcher-remove", [])
                            }
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
