// Run before the stylesheet to avoid flashing the wrong theme on reload.
(() => {
    const key = "xuanpu-theme";
    let preference = "system";
    try {
        const saved = localStorage.getItem(key);
        if (["light", "dark", "system"].includes(saved)) preference = saved;
    } catch (_) { /* Storage can be disabled in private or local-file previews. */ }
    const dark = window.matchMedia("(prefers-color-scheme: dark)").matches;
    document.documentElement.dataset.theme = preference === "system" ? (dark ? "dark" : "light") : preference;
    document.documentElement.dataset.themePreference = preference;
})();
