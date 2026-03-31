const THEME_KEY = "habit-theme";

function applyTheme(theme) {
    const root = document.documentElement;

    if (theme === "dark") {
        root.classList.add("dark-mode");
    } else {
        root.classList.remove("dark-mode");
    }

    localStorage.setItem(THEME_KEY, theme);

    if (typeof window.renderHabitsChart === "function") {
        window.renderHabitsChart();
    }
}

function initTheme() {
    const savedTheme = localStorage.getItem(THEME_KEY);
    if (savedTheme === "dark" || savedTheme === "light") {
        applyTheme(savedTheme);
    } else {
        applyTheme("light");
    }

    const toggleBtn = document.getElementById("themeToggle");
    if (toggleBtn) {
        toggleBtn.addEventListener("click", () => {
            const isDark = document.documentElement.classList.contains("dark-mode");
            applyTheme(isDark ? "light" : "dark");
        });
    }
}

document.addEventListener("DOMContentLoaded", initTheme);