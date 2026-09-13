/**
 * Idra le sezioni "File della categoria" quando la cartella e' sul client
 * (server Django non vede i file) usando l'helper locale.
 */
(function () {
    "use strict";

    function getCsrfToken() {
        var input = document.querySelector('input[name="csrfmiddlewaretoken"]');
        return input ? input.value : "";
    }

    function showToast(message, type) {
        if (window.SecurtekUI && typeof window.SecurtekUI.showToast === "function") {
            window.SecurtekUI.showToast(message, type);
            return;
        }
        if (window.SecurtekToast && typeof window.SecurtekToast.show === "function") {
            window.SecurtekToast.show(message, type);
        }
    }

    function nativeOpenIconClass(extension) {
        var ext = (extension || "").toLowerCase();
        if (ext === "doc" || ext === "docx") {
            return "ti-file-type-doc text-blue";
        }
        if (ext === "xls" || ext === "xlsx" || ext === "xlsm") {
            return "ti-file-type-xls text-green";
        }
        return "ti-launch";
    }

    function isOfficeExtension(extension) {
        var ext = (extension || "").toLowerCase();
        return ["doc", "docx", "xls", "xlsx", "xlsm"].indexOf(ext) >= 0;
    }

    function readPanelMeta(panel) {
        var metaNode = panel.querySelector(".js-cfa-data");
        var meta = {
            unlink_url: panel.getAttribute("data-unlink-url") || "",
            description_url: panel.getAttribute("data-description-url") || "",
            scollegati: [],
            descriptions: {},
        };
        if (metaNode) {
            try {
                var parsed = JSON.parse(metaNode.textContent || "{}");
                meta.unlink_url = parsed.unlink_url || meta.unlink_url;
                meta.description_url = parsed.description_url || meta.description_url;
                meta.scollegati = parsed.scollegati || [];
                meta.descriptions = parsed.descriptions || {};
            } catch (error) {
                // ignore
            }
        }
        return meta;
    }

    function bindDescriptionForm(form, descriptionsMap) {
        var input = form.querySelector(".js-file-description-input");
        if (!input) {
            return;
        }
        function saveIfChanged() {
            var currentValue = input.value.trim();
            var originalValue = (input.dataset.originalValue || "").trim();
            if (currentValue === originalValue || form._saving) {
                return;
            }
            form._saving = true;
            form.classList.remove("is-saved", "is-error");
            var formData = new FormData(form);
            formData.set("descrizione", input.value);
            fetch(form.action, {
                method: "POST",
                headers: {
                    "X-CSRFToken": getCsrfToken(),
                    "X-Requested-With": "XMLHttpRequest",
                    Accept: "application/json",
                },
                body: formData,
                credentials: "same-origin",
            })
                .then(function (response) {
                    return response.json().catch(function () {
                        return {};
                    }).then(function (data) {
                        if (!response.ok || !data.success) {
                            throw new Error(data.error || "Impossibile salvare la descrizione.");
                        }
                        return data;
                    });
                })
                .then(function (data) {
                    var savedValue = typeof data.descrizione === "string" ? data.descrizione : currentValue;
                    input.value = savedValue;
                    input.dataset.originalValue = savedValue;
                    var fileName = formData.get("file");
                    if (fileName) {
                        descriptionsMap[fileName] = savedValue;
                    }
                    form.classList.add("is-saved");
                })
                .catch(function () {
                    form.classList.add("is-error");
                })
                .finally(function () {
                    form._saving = false;
                });
        }
        input.addEventListener("blur", saveIfChanged);
        input.addEventListener("keydown", function (event) {
            if (event.key === "Enter") {
                event.preventDefault();
                saveIfChanged();
            }
        });
    }

    function renderPanelFiles(panel, files, meta) {
        var emptyEl = panel.querySelector(".js-client-folder-empty");
        var tableWrap = panel.querySelector(".js-client-folder-table");
        var rowsEl = panel.querySelector(".js-client-folder-rows");
        var statusEl = panel.querySelector(".js-client-folder-status");
        if (!rowsEl || !tableWrap) {
            return;
        }

        var scollegatiSet = new Set(meta.scollegati || []);
        var descriptionsMap = meta.descriptions || {};
        var helper = window.SecurtekDesktopFolder;
        var visible = (files || []).filter(function (file) {
            return !scollegatiSet.has(file.name || "");
        });

        rowsEl.innerHTML = "";
        visible.forEach(function (file) {
            var row = document.createElement("tr");
            var fileName = file.name || "";
            var extension = file.extension || "-";
            var fullPath = file.full_path || "";

            var nameCell = document.createElement("td");
            nameCell.textContent = fileName || "-";

            var descriptionCell = document.createElement("td");
            if (meta.description_url && fileName) {
                var form = document.createElement("form");
                form.method = "post";
                form.action = meta.description_url;
                form.className = "st-file-description-form";
                form.setAttribute("data-unsaved-guard", "false");
                var csrf = document.createElement("input");
                csrf.type = "hidden";
                csrf.name = "csrfmiddlewaretoken";
                csrf.value = getCsrfToken();
                var fileHidden = document.createElement("input");
                fileHidden.type = "hidden";
                fileHidden.name = "file";
                fileHidden.value = fileName;
                var descInput = document.createElement("input");
                descInput.type = "text";
                descInput.name = "descrizione";
                descInput.className = "form-control form-control-sm js-file-description-input";
                descInput.placeholder = "Aggiungi descrizione";
                var existing = descriptionsMap[fileName] || file.description || "";
                descInput.value = existing;
                descInput.dataset.originalValue = existing;
                form.appendChild(csrf);
                form.appendChild(fileHidden);
                form.appendChild(descInput);
                descriptionCell.appendChild(form);
                bindDescriptionForm(form, descriptionsMap);
            } else {
                descriptionCell.textContent = descriptionsMap[fileName] || file.description || "-";
            }

            var createdCell = document.createElement("td");
            createdCell.textContent = file.created_at || "-";
            var modifiedCell = document.createElement("td");
            modifiedCell.textContent = file.modified_at || "-";
            var typeCell = document.createElement("td");
            var badge = document.createElement("span");
            badge.className = "badge bg-secondary-lt";
            badge.textContent = extension;
            typeCell.appendChild(badge);
            var sizeCell = document.createElement("td");
            sizeCell.textContent = (file.size_kb || 0) + " KB";

            var actionsCell = document.createElement("td");
            actionsCell.className = "text-end st-file-actions";

            if (fullPath && helper && helper.openFile) {
                var openButton = document.createElement("button");
                openButton.type = "button";
                openButton.className = "btn btn-icon btn-outline-primary js-client-open-file";
                var office = isOfficeExtension(extension);
                openButton.title = office ? "Apri con applicazione originale" : "Apri file";
                openButton.innerHTML = '<i class="ti ' + (office ? nativeOpenIconClass(extension) : "ti-eye") + '"></i>';
                openButton.addEventListener("click", function () {
                    helper.openFile(fullPath).then(function () {
                        showToast(office ? "File aperto con l'applicazione originale." : "File aperto.", "success");
                    }).catch(function (error) {
                        showToast((error && error.message) || "Impossibile aprire il file.", "error");
                    });
                });
                actionsCell.appendChild(openButton);
            }

            if (meta.unlink_url && fileName) {
                var unlinkButton = document.createElement("button");
                unlinkButton.type = "button";
                unlinkButton.className = "btn btn-icon btn-outline-secondary js-delete-file";
                unlinkButton.title = "Scollega file dalla pratica";
                unlinkButton.dataset.deleteAction = meta.unlink_url;
                unlinkButton.dataset.deleteFile = fileName;
                unlinkButton.dataset.deleteMode = "unlink";
                unlinkButton.innerHTML = '<i class="ti ti-unlink"></i>';
                actionsCell.appendChild(unlinkButton);
            }

            if (fullPath && helper && helper.revealFile) {
                var revealButton = document.createElement("button");
                revealButton.type = "button";
                revealButton.className = "btn btn-icon btn-outline-secondary js-client-reveal-file";
                revealButton.title = "Apri cartella di origine";
                revealButton.innerHTML = '<i class="ti ti-folder-open"></i>';
                revealButton.addEventListener("click", function () {
                    helper.revealFile(fullPath).catch(function (error) {
                        showToast((error && error.message) || "Impossibile mostrare il file.", "error");
                    });
                });
                actionsCell.appendChild(revealButton);
            }

            if (!actionsCell.children.length) {
                actionsCell.textContent = "-";
            }

            row.appendChild(nameCell);
            row.appendChild(descriptionCell);
            row.appendChild(createdCell);
            row.appendChild(modifiedCell);
            row.appendChild(typeCell);
            row.appendChild(sizeCell);
            row.appendChild(actionsCell);
            rowsEl.appendChild(row);
        });

        var hasFiles = visible.length > 0;
        tableWrap.hidden = !hasFiles;
        if (emptyEl) {
            emptyEl.hidden = hasFiles;
            if (!hasFiles) {
                emptyEl.textContent = "Nessun file nella cartella.";
            }
        }
        if (statusEl) {
            statusEl.hidden = true;
            statusEl.textContent = "";
        }
    }

    function setPanelStatus(panel, text, isError) {
        var statusEl = panel.querySelector(".js-client-folder-status");
        var emptyEl = panel.querySelector(".js-client-folder-empty");
        if (statusEl) {
            statusEl.hidden = !text;
            statusEl.textContent = text || "";
            statusEl.classList.toggle("text-danger", !!isError);
            statusEl.classList.toggle("text-secondary", !isError);
        }
        if (text && emptyEl) {
            emptyEl.hidden = true;
        }
    }

    function hydratePanel(panel) {
        var cartella = (panel.getAttribute("data-cartella") || "").trim();
        var previewUrl = panel.getAttribute("data-preview-url") || "";
        var meta = readPanelMeta(panel);

        if (!cartella) {
            return Promise.resolve();
        }

        var helper = window.SecurtekDesktopFolder;
        if (!helper || !helper.fetchFolderPreview) {
            setPanelStatus(panel, "Helper cartelle non disponibile su questo computer.", true);
            return Promise.resolve();
        }

        setPanelStatus(panel, "Lettura file dalla cartella locale…", false);

        return helper
            .fetchFolderPreview(previewUrl, cartella)
            .then(function (data) {
                if (data.error) {
                    setPanelStatus(panel, data.error, true);
                    renderPanelFiles(panel, [], meta);
                    return;
                }
                renderPanelFiles(panel, data.files || [], meta);
                if (!(data.files || []).length) {
                    setPanelStatus(panel, "", false);
                } else if (data.truncated) {
                    setPanelStatus(panel, "Mostrati i primi 500 file. La cartella ne contiene di più.", false);
                } else {
                    setPanelStatus(panel, "", false);
                }
            })
            .catch(function (error) {
                renderPanelFiles(panel, [], meta);
                setPanelStatus(
                    panel,
                    (error && error.message) || "Impossibile leggere i file della cartella.",
                    true
                );
            });
    }

    function hydrateAll() {
        var panels = document.querySelectorAll(".js-client-folder-panel[data-cartella]");
        var chain = Promise.resolve();
        panels.forEach(function (panel) {
            chain = chain.then(function () {
                return hydratePanel(panel);
            });
        });
        return chain;
    }

    window.SecurtekClientFolderPanels = {
        hydrateAll: hydrateAll,
        hydratePanel: hydratePanel,
        renderPanelFiles: renderPanelFiles,
    };

    document.addEventListener("DOMContentLoaded", function () {
        hydrateAll();
    });
})();
