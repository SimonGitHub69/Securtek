(function () {
    "use strict";

    // Logout solo alla chiusura della finestra app (X), non sulle navigazioni interne.
    let leavingPage = false;
    let closingWindow = false;
    let closingTimer = null;
    let suppressUnloadPrompt = false;
    let suppressUnloadTimer = null;
    let sent = false;

    function clearClosingFlag() {
        closingWindow = false;
        if (closingTimer) {
            window.clearTimeout(closingTimer);
            closingTimer = null;
        }
    }

    function markLeavingPage() {
        leavingPage = true;
        suppressUnloadPrompt = false;
        clearClosingFlag();
        if (suppressUnloadTimer) {
            window.clearTimeout(suppressUnloadTimer);
            suppressUnloadTimer = null;
        }
    }

    function suppressUnload(durationMs) {
        suppressUnloadPrompt = true;
        clearClosingFlag();
        if (suppressUnloadTimer) {
            window.clearTimeout(suppressUnloadTimer);
        }
        suppressUnloadTimer = window.setTimeout(function () {
            suppressUnloadPrompt = false;
            suppressUnloadTimer = null;
        }, durationMs || 5000);
    }

    function sendLogout(logoutUrl) {
        const silentUrl = logoutUrl + (logoutUrl.indexOf("?") >= 0 ? "&" : "?") + "silent=1";
        try {
            if (navigator.sendBeacon) {
                navigator.sendBeacon(silentUrl, "");
                return;
            }
        } catch (error) {
            // fallback sotto
        }
        try {
            fetch(silentUrl, {
                method: "GET",
                keepalive: true,
                credentials: "same-origin",
            }).catch(function () {});
        } catch (error) {
            // ignore
        }
    }

    function initLogoutOnClose() {
        if (!document.body || document.body.dataset.logoutOnClose !== "1") {
            return;
        }

        const logoutUrl = document.body.dataset.logoutUrl || "/logout/";

        document.addEventListener("click", function (event) {
            const link = event.target.closest("a[href]");
            if (!link) {
                return;
            }

            const href = link.getAttribute("href");
            if (!href || href.charAt(0) === "#" || link.target === "_blank") {
                return;
            }
            if (/^(mailto:|tel:|javascript:)/i.test(href)) {
                suppressUnload(5000);
                return;
            }

            markLeavingPage();
        }, true);

        document.addEventListener("submit", function (event) {
            const form = event.target;
            if (!form || form.tagName !== "FORM") {
                return;
            }
            if (form.hasAttribute("hx-post") || form.hasAttribute("hx-get")) {
                return;
            }
            if (form.querySelector("[hx-post], [hx-get]")) {
                return;
            }

            markLeavingPage();
        }, true);

        document.addEventListener("keydown", function (event) {
            if (event.key === "F5" || ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "r")) {
                markLeavingPage();
            }
        }, true);

        // Indietro/avanti browser: navigazione interna, non chiusura finestra.
        window.addEventListener("popstate", function () {
            markLeavingPage();
        });

        window.addEventListener("pageshow", function () {
            leavingPage = false;
            sent = false;
            clearClosingFlag();
        });

        // Se l'utente annulla la chiusura o la pagina resta in primo piano, non logout.
        window.addEventListener("focus", clearClosingFlag);
        document.addEventListener("visibilitychange", function () {
            if (document.visibilityState === "visible") {
                clearClosingFlag();
            }
        });

        window.addEventListener("beforeunload", function (event) {
            if (leavingPage || suppressUnloadPrompt) {
                return;
            }

            closingWindow = true;
            if (closingTimer) {
                window.clearTimeout(closingTimer);
            }
            // Finestra breve: basta per il dialogo di conferma; poi il flag decade.
            closingTimer = window.setTimeout(function () {
                closingWindow = false;
                closingTimer = null;
            }, 2500);

            event.preventDefault();
            event.returnValue = " ";
            return event.returnValue;
        });

        window.addEventListener("pagehide", function (event) {
            if (event.persisted) {
                clearClosingFlag();
                return;
            }

            if (leavingPage || suppressUnloadPrompt) {
                leavingPage = false;
                return;
            }

            if (!closingWindow || sent) {
                return;
            }

            sent = true;
            sendLogout(logoutUrl);
        });
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initLogoutOnClose);
    } else {
        initLogoutOnClose();
    }
})();
