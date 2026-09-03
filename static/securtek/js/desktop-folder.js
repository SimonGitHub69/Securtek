(function () {
    "use strict";

    var HELPER_BASE = "http://127.0.0.1:18765";
    var HELPER_TIMEOUT_MS = 120000;
    var SERVER_TIMEOUT_MS = 330000;
    var HELPER_POPUP_FEATURES =
        "popup=yes,width=1,height=1,left=-10000,top=-10000,noopener=no,noreferrer=no";

    function isMacClient() {
        return /Mac|iPhone|iPad|iPod/.test(navigator.platform || "") ||
            /Mac OS X/.test(navigator.userAgent || "");
    }

    function looksLikeWindowsPath(pathValue) {
        return /^[A-Za-z]:[\\/]/.test(pathValue || "") ||
            (pathValue || "").indexOf("\\\\") === 0;
    }

    function looksLikeUnixPath(pathValue) {
        var value = (pathValue || "").trim();
        return value.indexOf("/") === 0 || value.indexOf("~/") === 0;
    }

    function parseJsonResponse(response) {
        var contentType = response.headers.get("content-type") || "";
        if (contentType.indexOf("application/json") === -1) {
            return response.text().then(function (text) {
                if (
                    response.redirected ||
                    (response.url && response.url.indexOf("/login") >= 0) ||
                    /name=["']username["']/i.test(text)
                ) {
                    throw new Error("Sessione scaduta: effettua di nuovo il login.");
                }
                throw new Error("Risposta non valida dal server.");
            });
        }
        return response.json().catch(function () {
            return {};
        });
    }

    function fetchJson(url, options, timeoutMs) {
        var controller = typeof AbortController !== "undefined" ? new AbortController() : null;
        var timer = null;
        var opts = Object.assign({ credentials: "same-origin" }, options || {});
        if (controller) {
            opts.signal = controller.signal;
            timer = window.setTimeout(function () {
                controller.abort();
            }, timeoutMs || 15000);
        }
        return fetch(url, opts).finally(function () {
            if (timer) {
                window.clearTimeout(timer);
            }
        }).then(function (response) {
            return parseJsonResponse(response).then(function (data) {
                return { response: response, data: data };
            });
        });
    }

    function helperHealth() {
        return fetchJson(HELPER_BASE + "/health", { method: "GET", mode: "cors" }, 1500)
            .then(function (result) {
                return !!(result.response.ok && result.data && result.data.ok);
            })
            .catch(function () {
                return false;
            });
    }

    function pickViaHelper(title) {
        return fetchJson(
            HELPER_BASE + "/pick-folder",
            {
                method: "POST",
                mode: "cors",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ title: title || "Seleziona cartella pratica" }),
            },
            HELPER_TIMEOUT_MS
        ).then(function (result) {
            if (!result.response.ok || result.data.error) {
                throw new Error(result.data.error || "Helper locale: selezione fallita.");
            }
            return result.data.path || "";
        });
    }

    function helperPopupCallbackId() {
        return "st-" + Date.now() + "-" + Math.random().toString(36).slice(2, 10);
    }

    function waitForHelperPopup(messageType, callbackId, timeoutMs) {
        return new Promise(function (resolve, reject) {
            var timer = null;
            var pollTimer = null;
            var settled = false;

            function cleanup() {
                if (timer) {
                    window.clearTimeout(timer);
                }
                if (pollTimer) {
                    window.clearInterval(pollTimer);
                }
                window.removeEventListener("message", onMessage);
            }

            function finishOk(data) {
                if (settled) {
                    return;
                }
                settled = true;
                cleanup();
                resolve(data);
            }

            function finishErr(error) {
                if (settled) {
                    return;
                }
                settled = true;
                cleanup();
                reject(error);
            }

            function onMessage(event) {
                if (event.origin !== "http://127.0.0.1:18765") {
                    return;
                }
                var data = event.data;
                if (!data || data.type !== messageType) {
                    return;
                }
                if (data.error) {
                    finishErr(new Error(data.error));
                    return;
                }
                finishOk(data);
            }

            window.addEventListener("message", onMessage);
            timer = window.setTimeout(function () {
                finishErr(new Error("Timeout helper locale."));
            }, timeoutMs || HELPER_TIMEOUT_MS);

            if (callbackId) {
                pollTimer = window.setInterval(function () {
                    fetch(HELPER_BASE + "/result?id=" + encodeURIComponent(callbackId), {
                        method: "GET",
                        mode: "cors",
                    })
                        .then(function (response) {
                            if (!response.ok) {
                                return null;
                            }
                            return response.json();
                        })
                        .then(function (data) {
                            if (!data || !data.payload || data.payload.type !== messageType) {
                                return;
                            }
                            if (data.payload.error) {
                                finishErr(new Error(data.payload.error));
                                return;
                            }
                            finishOk(data.payload);
                        })
                        .catch(function () {
                            /* retry */
                        });
                }, 400);
            }
        });
    }

    function pickViaHelperPopup(title) {
        var callbackId = helperPopupCallbackId();
        var openerOrigin = window.location.origin || "*";
        var safeTitle = title || "Seleziona cartella pratica";
        var url =
            HELPER_BASE +
            "/pick-ui?title=" +
            encodeURIComponent(safeTitle) +
            "&opener=" +
            encodeURIComponent(openerOrigin) +
            "&cb=" +
            encodeURIComponent(callbackId);
        var popup = window.open(
            url,
            "securtek-folder-picker",
            HELPER_POPUP_FEATURES
        );
        if (!popup) {
            return Promise.reject(new Error("Popup bloccato. Consenti i popup per Securtek e riprova."));
        }
        return waitForHelperPopup("securtek-folder-picked", callbackId, HELPER_TIMEOUT_MS)
            .then(function (data) {
                return data.path || "";
            });
    }

    function openViaHelper(path) {
        return fetchJson(
            HELPER_BASE + "/open-folder",
            {
                method: "POST",
                mode: "cors",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ path: path }),
            },
            15000
        ).then(function (result) {
            if (!result.response.ok || result.data.error) {
                throw new Error(result.data.error || "Helper locale: apertura fallita.");
            }
            return result.data.message || "Cartella aperta.";
        });
    }

    function revealViaHelper(path) {
        return fetchJson(
            HELPER_BASE + "/reveal-file",
            {
                method: "POST",
                mode: "cors",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ path: path }),
            },
            15000
        ).then(function (result) {
            if (!result.response.ok || result.data.error) {
                throw new Error(result.data.error || "Helper locale: impossibile mostrare il file.");
            }
            return result.data.message || "File mostrato in Explorer/Finder.";
        });
    }

    function isLocalClientPath(pathValue) {
        return looksLikeWindowsPath(pathValue) || looksLikeUnixPath(pathValue);
    }

    function listFolder(path) {
        return fetchJson(
            HELPER_BASE + "/list-folder",
            {
                method: "POST",
                mode: "cors",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ path: path }),
            },
            60000
        ).then(function (result) {
            if (!result.response.ok || result.data.error) {
                if (result.response.status === 404) {
                    throw new Error(
                        "Helper da aggiornare: riesegui InstallClient.command (Mac) o " +
                        "SecurtekDesktopHelper.bat (Windows), poi ricarica Securtek."
                    );
                }
                throw new Error(result.data.error || "Impossibile leggere la cartella su questo computer.");
            }
            return result.data.files || [];
        });
    }

    function listFolderWithMeta(path) {
        return fetchJson(
            HELPER_BASE + "/list-folder",
            {
                method: "POST",
                mode: "cors",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ path: path }),
            },
            60000
        ).then(function (result) {
            if (!result.response.ok || result.data.error) {
                if (result.response.status === 404) {
                    throw new Error(
                        "Helper da aggiornare: riesegui InstallClient.command (Mac) o " +
                        "SecurtekDesktopHelper.bat (Windows), poi ricarica Securtek."
                    );
                }
                throw new Error(result.data.error || "Impossibile leggere la cartella su questo computer.");
            }
            return {
                files: result.data.files || [],
                truncated: !!result.data.truncated,
            };
        });
    }

    function listFolderViaPopup(path) {
        var callbackId = helperPopupCallbackId();
        var openerOrigin = window.location.origin || "*";
        var url =
            HELPER_BASE +
            "/list-ui?path=" +
            encodeURIComponent(path) +
            "&opener=" +
            encodeURIComponent(openerOrigin) +
            "&cb=" +
            encodeURIComponent(callbackId);
        var popup = window.open(
            url,
            "securtek-folder-list",
            HELPER_POPUP_FEATURES
        );
        if (!popup) {
            return Promise.reject(new Error("Popup bloccato. Consenti i popup per Securtek e riprova."));
        }
        return waitForHelperPopup("securtek-folder-list", callbackId, 60000)
            .then(function (data) {
                return {
                    files: data.files || [],
                    truncated: !!data.truncated,
                };
            });
    }

    function listFolderLocal(path) {
        var folder = (path || "").trim();
        if (!folder) {
            return Promise.resolve({ files: [], truncated: false });
        }
        if (isBrowsingOnServerLoopback()) {
            return listFolderWithMeta(folder);
        }
        return listFolderWithMeta(folder).catch(function () {
            return listFolderViaPopup(folder);
        });
    }

    function fetchFolderPreview(previewUrl, folderPath) {
        var folder = (folderPath || "").trim();
        if (!folder) {
            return Promise.resolve({ files: [], error: "" });
        }

        function viaServer() {
            var serverUrl =
                previewUrl +
                (previewUrl.indexOf("?") >= 0 ? "&" : "?") +
                "path=" +
                encodeURIComponent(folder);
            return fetchJson(
                serverUrl,
                {
                    headers: {
                        "X-Requested-With": "XMLHttpRequest",
                        "Accept": "application/json",
                    },
                },
                30000
            ).then(function (result) {
                var data = result.data || {};
                if (result.response.ok && !data.error && !data.is_link) {
                    return data;
                }
                throw new Error(data.error || "Cartella non trovata sul server.");
            });
        }

        function viaHelper() {
            return listFolderLocal(folder).then(function (result) {
                return {
                    files: result.files || [],
                    error: "",
                    is_link: false,
                    from_helper: true,
                    truncated: !!result.truncated,
                };
            });
        }

        if (!isBrowsingOnServerLoopback() && isLocalClientPath(folder)) {
            return viaHelper().catch(function (helperErr) {
                return viaServer().catch(function () {
                    throw helperErr;
                });
            });
        }

        return viaServer().catch(function (serverErr) {
            return viaHelper().catch(function () {
                throw serverErr;
            });
        });
    }

    function pickViaServer(pickerUrl) {
        return fetchJson(
            pickerUrl,
            {
                headers: {
                    "X-Requested-With": "XMLHttpRequest",
                    "Accept": "application/json",
                },
            },
            SERVER_TIMEOUT_MS
        ).then(function (result) {
            if (!result.response.ok || result.data.error) {
                throw new Error(result.data.error || "Impossibile scegliere la cartella sul server.");
            }
            return result.data.path || "";
        });
    }

    function openViaServer(openUrl, path) {
        var url = openUrl + (openUrl.indexOf("?") >= 0 ? "&" : "?") + "path=" + encodeURIComponent(path);
        return fetchJson(
            url,
            {
                headers: {
                    "X-Requested-With": "XMLHttpRequest",
                    "Accept": "application/json",
                },
            },
            30000
        ).then(function (result) {
            if (!result.response.ok || result.data.error || result.data.success === false) {
                throw new Error(
                    result.data.error ||
                        "Impossibile aprire la cartella sul server."
                );
            }
            return result.data.message || "Cartella aperta.";
        });
    }

    function isWindowsClient() {
        return /Win/i.test(navigator.userAgent || "") || /Win/i.test(navigator.platform || "");
    }

    function isBrowsingOnServerLoopback() {
        var host = window.location.hostname || "";
        return host === "127.0.0.1" || host === "localhost" || host === "[::1]";
    }

    function helperInstallHint() {
        if (isMacClient()) {
            return (
                "Helper cartelle non attivo su questo Mac. " +
                "Copia la cartella deploy/macos-client sul Mac client e fai doppio clic su InstallClient.command, " +
                "poi ricarica Securtek."
            );
        }
        return (
            "Helper locale non disponibile. Avvia SecurtekDesktopHelper.bat su questo PC."
        );
    }

    function pickWithClientHelper(title) {
        return helperHealth().then(function (ok) {
            if (!ok) {
                throw new Error(helperInstallHint());
            }
            return pickViaHelper(title);
        });
    }

    /**
     * Helper sul computer dell'utente (Finder/Explorer locali).
     * Locale: chiamata diretta → Explorer subito, senza popup.
     * Remoto: popup invisibile solo se il browser blocca la chiamata diretta.
     */
    function pickFolder(pickerUrl, title) {
        return pickWithClientHelper(title).catch(function (helperErr) {
            if (!isBrowsingOnServerLoopback()) {
                return pickViaHelperPopup(title).catch(function () {
                    throw helperErr;
                });
            }
            return pickViaServer(pickerUrl).catch(function () {
                throw helperErr;
            });
        });
    }

    function openFolder(openUrl, path) {
        var folder = (path || "").trim();
        if (!folder) {
            return Promise.reject(new Error("Inserisci o scegli prima una cartella."));
        }

        if (looksLikeWindowsPath(folder)) {
            return helperHealth().then(function (ok) {
                if (!ok) {
                    throw new Error(
                        "Percorso Windows: avvia SecurtekDesktopHelper.bat sul PC Windows " +
                        "dove si trova la cartella D:/."
                    );
                }
                return openViaHelper(folder);
            });
        }

        return helperHealth().then(function (ok) {
            if (ok) {
                return openViaHelper(folder).catch(function (helperErr) {
                    return openViaServer(openUrl, folder).catch(function () {
                        throw helperErr;
                    });
                });
            }
            return openViaServer(openUrl, folder).catch(function (serverErr) {
                if (isMacClient() || looksLikeUnixPath(folder)) {
                    throw new Error(helperInstallHint());
                }
                throw serverErr;
            });
        });
    }

    function resolveCartellaField(button) {
        var targetId = button.getAttribute("data-cartella-target");
        if (targetId) {
            var byId = document.getElementById(targetId);
            if (byId) {
                return byId;
            }
        }

        var scope =
            button.closest(".st-folder-field") ||
            button.closest("tr.js-formset-row") ||
            button.closest("form") ||
            document;

        var byClass =
            scope.querySelector("input.js-cartella-input") ||
            scope.querySelector('input[data-securtek-cartella="1"]') ||
            scope.querySelector('input[data-original-name*="cartella"]');
        if (byClass) {
            return byClass;
        }

        var group = button.closest(".input-group");
        if (group) {
            var inputs = group.querySelectorAll("input");
            for (var i = 0; i < inputs.length; i++) {
                var candidate = inputs[i];
                var type = (candidate.getAttribute("type") || "text").toLowerCase();
                if (type !== "hidden" && type !== "file" && type !== "checkbox" && type !== "radio") {
                    return candidate;
                }
            }
        }

        return (
            scope.querySelector('input[name*="cartella"]') ||
            scope.querySelector('input[id*="cartella"]')
        );
    }

    window.SecurtekDesktopFolder = {
        helperBase: HELPER_BASE,
        isMacClient: isMacClient,
        pickFolder: pickFolder,
        openFolder: openFolder,
        helperHealth: helperHealth,
        listFolder: listFolder,
        revealFile: revealViaHelper,
        fetchFolderPreview: fetchFolderPreview,
        resolveCartellaField: resolveCartellaField,
    };
})();
