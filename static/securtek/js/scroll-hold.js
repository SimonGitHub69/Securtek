(function () {
    "use strict";

    var STORAGE_KEY = "securtek:personale-return";

    function normalizePath(path) {
        var value = String(path || "");
        if (!value) {
            return "/";
        }
        if (value.length > 1 && value.charAt(value.length - 1) === "/") {
            return value.slice(0, -1);
        }
        return value;
    }

    function readStored() {
        try {
            return JSON.parse(sessionStorage.getItem(STORAGE_KEY) || "null");
        } catch (error) {
            return null;
        }
    }

    function remember(returnPath) {
        sessionStorage.setItem(
            STORAGE_KEY,
            JSON.stringify({
                path: normalizePath(returnPath || window.location.pathname),
                scrollY: window.scrollY || window.pageYOffset || 0,
                focusPersonale: true,
            })
        );
    }

    function expandPersonaleSection() {
        var targets = [
            "practice-technicians-section",
            "pratica-form-personale-section",
        ];
        var i;
        for (i = 0; i < targets.length; i += 1) {
            var section = document.getElementById(targets[i]);
            var toggle = document.querySelector(
                '.st-collapse-toggle[data-collapse-target="' + targets[i] + '"]'
            );
            if (!section || !toggle) {
                continue;
            }
            section.hidden = false;
            toggle.classList.remove("is-collapsed");
            toggle.setAttribute("aria-expanded", "true");
            toggle.title = "Comprimi sezione";
            document
                .querySelectorAll('.st-section-header[data-collapse-target="' + targets[i] + '"]')
                .forEach(function (header) {
                    header.classList.remove("is-collapsed");
                });
        }
    }

    function messageOffset() {
        var alerts = document.querySelectorAll(".container-xl > .alert");
        var total = 0;
        alerts.forEach(function (alert) {
            total += alert.offsetHeight;
            var style = window.getComputedStyle(alert);
            total += (parseFloat(style.marginTop) || 0) + (parseFloat(style.marginBottom) || 0);
        });
        return total;
    }

    function release() {
        document.documentElement.classList.remove("st-hold-scroll");
    }

    function restore() {
        var data = window.__securtekHoldScroll || null;
        if (!data) {
            data = readStored();
            if (
                !data ||
                normalizePath(data.path) !== normalizePath(window.location.pathname)
            ) {
                release();
                return false;
            }
        }

        sessionStorage.removeItem(STORAGE_KEY);
        window.__securtekHoldScroll = null;

        if (data.focusPersonale) {
            expandPersonaleSection();
        }

        var top = (Number(data.scrollY) || 0) + messageOffset();
        window.scrollTo(0, top);
        release();
        return true;
    }

    window.SecurtekScrollHold = {
        remember: remember,
        restore: restore,
        release: release,
        normalizePath: normalizePath,
        storageKey: STORAGE_KEY,
    };

    window.setTimeout(release, 2500);

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", restore);
    } else {
        restore();
    }
})();
