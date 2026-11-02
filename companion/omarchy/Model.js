.pragma library

var providers = [
    {value: "codex", label: "Codex"},
    {value: "claude", label: "Claude Code"},
    {value: "ollama", label: "Local LLM · Ollama"},
    {value: "local", label: "Local LLM · compatible server"}
];

function isLocal(provider) {
    return provider === "ollama" || provider === "local";
}

function fields(config, provider) {
    return {
        model: (config.models || {})[provider] || "",
        endpoint: (config.endpoints || {})[provider] || ""
    };
}

function endpointHint(provider) {
    return provider === "ollama" ? "http://127.0.0.1:11434" : "http://127.0.0.1:1234/v1";
}

function localPath(url) {
    if (url.indexOf("file:///") !== 0)
        throw new Error("The companion must be loaded from a local installation.");
    return decodeURIComponent(url.slice(7));
}

function modelChoices(value) {
    if (!Array.isArray(value))
        throw new Error("The model server returned an invalid model list.");
    // Match the CLI's model-ID grammar; do not offer remote server metadata.
    return value.filter(function(name) {
        return typeof name === "string" && name.length > 0 && name.length <= 256
            && name[0] !== "-" && /^[A-Za-z0-9_.:/\[\]-]+$/.test(name);
    });
}
