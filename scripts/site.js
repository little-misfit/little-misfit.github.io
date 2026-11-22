(() => {
    const root = document.documentElement;
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    const toggle = document.querySelector("[data-theme-toggle]");
    const modes = ["light", "dark", "system"];
    const labels = { light: "Day", dark: "Night", system: "System" };
    const themeColor = document.querySelector('meta[name="theme-color"]');
    let preference = root.dataset.themePreference || "system";

    function applyTheme() {
        const theme = preference === "system" ? (media.matches ? "dark" : "light") : preference;
        root.dataset.theme = theme;
        root.dataset.themePreference = preference;
        const next = modes[(modes.indexOf(preference) + 1) % modes.length];
        const current = preference === "system" ? `System (${labels[theme]})` : labels[preference];
        const label = `Theme: ${current}. Switch to ${labels[next]}.`;
        toggle.dataset.mode = preference;
        toggle.setAttribute("aria-label", label);
        toggle.title = label;
        if (themeColor) themeColor.content = theme === "dark" ? "#17282e" : "#f3f5ef";
    }

    toggle.addEventListener("click", () => {
        preference = modes[(modes.indexOf(preference) + 1) % modes.length];
        try { localStorage.setItem("xuanpu-theme", preference); } catch (_) {}
        applyTheme();
    });
    media.addEventListener("change", () => {
        if (preference === "system") applyTheme();
    });
    window.addEventListener("storage", event => {
        if (event.key !== "xuanpu-theme" && event.key !== null) return;
        preference = ["light", "dark", "system"].includes(event.newValue) ? event.newValue : "system";
        applyTheme();
    });
    applyTheme();
    root.dataset.enhanced = "";
})();
