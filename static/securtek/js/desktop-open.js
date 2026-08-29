(function () {
    "use strict";

    const TOAST_ID = "st-desktop-open-toast";
    const LOG_PREFIX = "[Securtek desktop-open]";

    function getCsrfToken() {
        const input = document.querySelector('input[name="csrfmiddlewaretoken"]');
        return input ? input.value : "";
    }

    function ensureToastElement() {
        let toast = document.getElementById(TOAST_ID);
        if (toast) {
            return toast;
        }

        toast = document.createElement("div");
        toast.id = TOAST_ID;
        toast.setAttribute("role", "status");
        toast.setAttribute("aria-live", "polite");
        toast.style.cssText = [
            "position:fixed",
            "right:1rem",
            "bottom:1rem",
            "z-index:1090",
            "max-width:24rem",
            "padding:0.75rem 1rem",
            "border-radius:8px",
            "box-shadow:0 0.5rem 1.5rem rgba(15,23,42,0.18)",
            "font-size:0.875rem",
            "line-height:1.4",
            "display:none",
        ].join(";");
        document.body.appendChild(toast);
        return toast;
    }

    function showToast(message, type, durationMs) {
        const toast = ensureToastElement();
        const isError = type === "error";
        const hideAfter = durationMs || (isError ? 6000 : 3000);

        toast.textContent = message;
        toast.style.display = "block";
        toast.style.background = isError ? "#fde8e8" : "#e8f5ec";
        toast.style.color = isError ? "#9b1c1c" : "#1a5632";
        toast.style.border = isError ? "1px solid #f8b4b4" : "1px solid #b7e1c1";

        window.clearTimeout(toast._hideTimeout);
        toast._hideTimeout = window.setTimeout(function () {
            toast.style.display = "none";
        }, hideAfter);
    }

    function setButtonLoading(button, loading) {
        if (!button.dataset.desktopOpenOriginalHtml) {
            button.dataset.desktopOpenOriginalHtml = button.innerHTML;
        }

        button.disabled = loading;
        button.classList.toggle("disabled", loading);
        button.setAttribute("aria-busy", loading ? "true" : "false");

        if (loading) {
            button.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>';
            return;
        }

        button.innerHTML = button.dataset.desktopOpenOriginalHtml;
    }

    async function requestDesktopOpen(url) {
        let response;

        try {
            response = await fetch(url, {
                method: "GET",
                headers: {
                    "X-Requested-With": "XMLHttpRequest",
                    "Accept": "application/json",
                    "X-CSRFToken": getCsrfToken(),
                },
                credentials: "same-origin",
            });
        } catch (error) {
            console.error(LOG_PREFIX, "fetch failed", { url: url, error: error });
            throw new Error("Impossibile contattare il server.");
        }

        const contentType = response.headers.get("Content-Type") || "";
        let data = {};

        try {
            if (contentType.includes("application/json")) {
                data = await response.json();
            } else {
                const body = await response.text();
                console.error(LOG_PREFIX, "non-JSON response", {
                    url: url,
                    status: response.status,
                    contentType: contentType,
                    bodyPreview: body.slice(0, 240),
                });
                throw new Error("Risposta non valida dal server.");
            }
        } catch (error) {
            if (error.message === "Risposta non valida dal server.") {
                throw error;
            }
            console.error(LOG_PREFIX, "JSON parse failed", {
                url: url,
                status: response.status,
                contentType: contentType,
                error: error,
            });
            throw new Error("Risposta non valida dal server.");
        }

        if (!response.ok || data.success === false || data.opened === false || data.error) {
            console.error(LOG_PREFIX, "desktop open rejected", {
                url: url,
                status: response.status,
                data: data,
            });
            throw new Error(data.error || data.message || "Operazione non riuscita.");
        }

        return data;
    }

    async function handleDesktopOpen(button, url, options) {
        if (!url || button.disabled) {
            if (!url) {
                console.error(LOG_PREFIX, "missing data-open-url on button", button);
            }
            return;
        }

        const opts = options || {};
        setButtonLoading(button, true);
        try {
            const data = await requestDesktopOpen(url);
            const message = data.message || opts.fallbackSuccessMessage;
            if (message) {
                showToast(message, "success", opts.successDurationMs);
            }
        } catch (error) {
            console.error(LOG_PREFIX, "handleDesktopOpen failed", {
                url: url,
                error: error,
            });
            showToast(error.message || "Operazione non riuscita.", "error");
        } finally {
            setButtonLoading(button, false);
        }
    }

    document.addEventListener("click", function (event) {
        const folderButton = event.target.closest(".js-open-pratica-folder");
        if (folderButton) {
            event.preventDefault();
            if (!folderButton.dataset.openUrl) {
                console.error(LOG_PREFIX, "folder button without data-open-url", folderButton);
                showToast("URL apertura cartella mancante.", "error");
                return;
            }
            handleDesktopOpen(folderButton, folderButton.dataset.openUrl, {
                fallbackSuccessMessage:
                    "Cartella aperta. Se Explorer resta dietro al browser, clicca la sua icona nella barra applicazioni.",
                successDurationMs: 4000,
            });
            return;
        }

        const fileButton = event.target.closest(".js-open-pratica-file");
        if (!fileButton || !fileButton.dataset.openUrl) {
            return;
        }

        event.preventDefault();

        if (fileButton.dataset.nativeOpen === "1") {
            handleDesktopOpen(fileButton, fileButton.dataset.openUrl);
            return;
        }

        window.open(fileButton.dataset.openUrl, "_blank", "noopener");
    });

    window.SecurtekUI = window.SecurtekUI || {};
    window.SecurtekUI.showToast = showToast;
    window.SecurtekUI.requestDesktopOpen = requestDesktopOpen;
})();
