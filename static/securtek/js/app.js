function getCurrentTheme() {
    return document.documentElement.getAttribute("data-bs-theme") || "light";
}

function applyTheme(theme) {
    const normalizedTheme = theme === "dark" ? "dark" : "light";
    const toggleButton = document.querySelector("[data-theme-toggle]");
    const toggleIcon = document.querySelector("[data-theme-toggle-icon]");
    const label = normalizedTheme === "dark" ? "Attiva tema chiaro" : "Attiva tema scuro";

    document.documentElement.setAttribute("data-bs-theme", normalizedTheme);
    localStorage.setItem("securtek-theme", normalizedTheme);

    if (toggleButton) {
        toggleButton.setAttribute("aria-label", label);
        toggleButton.setAttribute("title", label);
    }

    if (toggleIcon) {
        toggleIcon.classList.toggle("ti-moon", normalizedTheme !== "dark");
        toggleIcon.classList.toggle("ti-sun", normalizedTheme === "dark");
    }
}

function isSidebarCollapsed() {
    return document.documentElement.classList.contains("st-sidebar-collapsed");
}

function applySidebarCollapsed(collapsed) {
    const toggleButtons = document.querySelectorAll("[data-sidebar-toggle]");
    const label = collapsed ? "Espandi menu" : "Comprimi menu";

    document.documentElement.classList.toggle("st-sidebar-collapsed", collapsed);

    try {
        localStorage.setItem("securtek-sidebar", collapsed ? "collapsed" : "expanded");
    } catch (error) {
        // ignore storage errors
    }

    toggleButtons.forEach(function (toggleButton) {
        const toggleIcon = toggleButton.querySelector("[data-sidebar-toggle-icon]");
        const toggleLabel = toggleButton.querySelector(".st-sidebar-toggle-label");

        toggleButton.setAttribute("aria-expanded", collapsed ? "false" : "true");
        toggleButton.setAttribute("aria-label", label);
        toggleButton.setAttribute("title", label);

        if (toggleIcon) {
            toggleIcon.classList.toggle("ti-layout-sidebar-left-collapse", !collapsed);
            toggleIcon.classList.toggle("ti-layout-sidebar-left-expand", collapsed);
            toggleIcon.classList.toggle("ti-menu-2", false);
        }

        if (toggleLabel) {
            toggleLabel.textContent = collapsed ? "Espandi" : "Comprimi";
        }
    });
}

document.addEventListener("DOMContentLoaded", function () {
    const themeToggle = document.querySelector("[data-theme-toggle]");

    applyTheme(getCurrentTheme());
    applySidebarCollapsed(isSidebarCollapsed());

    if (themeToggle) {
        themeToggle.addEventListener("click", function () {
            applyTheme(getCurrentTheme() === "dark" ? "light" : "dark");
        });
    }

    document.querySelectorAll("[data-sidebar-toggle]").forEach(function (sidebarToggle) {
        sidebarToggle.addEventListener("click", function () {
            applySidebarCollapsed(!isSidebarCollapsed());
        });
    });

    function submenuStorageKey(key) {
        return "securtek-submenu:" + key;
    }

    function setSubmenuCollapsed(submenu, collapsed, persist) {
        const key = submenu.dataset.submenu;
        const toggle = submenu.querySelector("[data-submenu-toggle]");
        const panel = submenu.querySelector("[data-submenu-panel]");

        submenu.classList.toggle("is-collapsed", collapsed);

        if (toggle) {
            toggle.setAttribute("aria-expanded", collapsed ? "false" : "true");
            toggle.title = collapsed ? "Espandi " + (toggle.querySelector(".st-nav-submenu-title")?.textContent || "menu") : toggle.querySelector(".st-nav-submenu-title")?.textContent || "menu";
        }

        if (panel) {
            panel.hidden = collapsed;
        }

        if (persist && key) {
            try {
                localStorage.setItem(submenuStorageKey(key), collapsed ? "1" : "0");
            } catch (error) {
                // ignore storage errors
            }
        }
    }

    document.querySelectorAll(".st-nav-submenu[data-submenu]").forEach(function (submenu) {
        const key = submenu.dataset.submenu;
        const toggle = submenu.querySelector("[data-submenu-toggle]");
        const hasActiveLink = Boolean(submenu.querySelector(".st-nav-link.active"));
        let collapsed = false;

        try {
            collapsed = localStorage.getItem(submenuStorageKey(key)) === "1";
        } catch (error) {
            collapsed = false;
        }

        // Se la pagina corrente e' in questo sotto-menu, tienilo aperto.
        if (hasActiveLink) {
            collapsed = false;
        }

        setSubmenuCollapsed(submenu, collapsed, false);

        if (toggle) {
            toggle.addEventListener("click", function () {
                setSubmenuCollapsed(submenu, !submenu.classList.contains("is-collapsed"), true);
            });
        }
    });
});

document.addEventListener("DOMContentLoaded", function () {
    const guardedForms = Array.from(document.querySelectorAll('form[method="post"]')).filter(function (form) {
        const hasEditableFields = form.querySelector(
            'input:not([type="hidden"]):not([type="submit"]):not([type="button"]), textarea, select'
        );

        return form.dataset.unsavedGuard !== "false" && Boolean(hasEditableFields);
    });

    if (!guardedForms.length) {
        return;
    }

    let hasUnsavedChanges = false;
    let isSubmitting = false;

    function markUnsaved() {
        if (!isSubmitting) {
            hasUnsavedChanges = true;
        }
    }

    guardedForms.forEach(function (form) {
        form.addEventListener("input", markUnsaved);
        form.addEventListener("change", markUnsaved);
        form.addEventListener("submit", function () {
            isSubmitting = true;
            hasUnsavedChanges = false;
        });
    });

    document.addEventListener("click", function (event) {
        const button = event.target.closest("button");

        if (!button || button.type === "submit" || button.dataset.unsavedIgnore === "true") {
            return;
        }

        const form = button.closest('form[method="post"]');

        if (form && guardedForms.includes(form)) {
            markUnsaved();
        }
    });

    window.addEventListener("beforeunload", function (event) {
        if (!hasUnsavedChanges || isSubmitting) {
            return;
        }

        event.preventDefault();
        event.returnValue = "";
    });
});
