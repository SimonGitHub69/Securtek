(function () {
    function findAddressRow(element) {
        return element.closest(".js-indirizzo-row, .card-body, form, tr, .st-form-panel") || document;
    }

    function setSelectOptions(select, items, selectedValue) {
        const current = selectedValue != null && selectedValue !== ""
            ? String(selectedValue)
            : String(select.value || "");
        select.innerHTML = "";

        const empty = document.createElement("option");
        empty.value = "";
        empty.textContent = "---------";
        select.appendChild(empty);

        items.forEach(function (item) {
            const option = document.createElement("option");
            option.value = String(item.id);
            option.textContent = item.nome;
            option.dataset.cap = item.cap || "";
            option.dataset.provinciaId = item.provincia_id ? String(item.provincia_id) : "";
            if (String(item.id) === current || item.nome === current) {
                option.selected = true;
            }
            select.appendChild(option);
        });

        if (current && select.value !== current) {
            const orphan = document.createElement("option");
            orphan.value = current;
            orphan.textContent = current;
            orphan.selected = true;
            select.appendChild(orphan);
        }
    }

    async function loadComuni(provinciaSelect, preserveSelection) {
        const row = findAddressRow(provinciaSelect);
        const comuneSelect = row.querySelector(".js-comune-select");
        const capInput = row.querySelector(".js-cap-input");
        if (!comuneSelect) {
            return;
        }

        const provinciaId = (provinciaSelect.value || "").trim();
        const urlBase = provinciaSelect.dataset.comuniUrl || "/anagrafiche/api/comuni/";
        const selectedComune = preserveSelection === false ? "" : comuneSelect.value;

        if (!provinciaId) {
            setSelectOptions(comuneSelect, [], "");
            return;
        }

        try {
            const response = await fetch(
                urlBase + "?provincia_id=" + encodeURIComponent(provinciaId),
                { headers: { "X-Requested-With": "XMLHttpRequest" } }
            );
            const data = await response.json();
            setSelectOptions(comuneSelect, data.comuni || [], selectedComune);

            const selected = comuneSelect.options[comuneSelect.selectedIndex];
            if (selected && selected.dataset.cap && capInput && !capInput.value) {
                capInput.value = selected.dataset.cap;
            }
        } catch (error) {
            // Mantieni le opzioni correnti in caso di errore di rete.
        }
    }

    function onComuneChange(comuneSelect) {
        const row = findAddressRow(comuneSelect);
        const capInput = row.querySelector(".js-cap-input");
        const provinciaSelect = row.querySelector(".js-provincia-select");
        const selected = comuneSelect.options[comuneSelect.selectedIndex];
        if (capInput && selected && selected.dataset.cap) {
            capInput.value = selected.dataset.cap;
        }
        if (provinciaSelect && selected && selected.dataset.provinciaId && !provinciaSelect.value) {
            provinciaSelect.value = selected.dataset.provinciaId;
        }
    }

    function bindAddressRow(root) {
        root.querySelectorAll(".js-provincia-select").forEach(function (select) {
            if (select.dataset.bound === "1") {
                return;
            }
            select.dataset.bound = "1";
            select.addEventListener("change", function () {
                loadComuni(select, false);
            });
            if (select.value) {
                loadComuni(select, true);
            }
        });

        root.querySelectorAll(".js-comune-select").forEach(function (select) {
            if (select.dataset.bound === "1") {
                return;
            }
            select.dataset.bound = "1";
            select.addEventListener("change", function () {
                onComuneChange(select);
            });
        });
    }

    document.addEventListener("DOMContentLoaded", function () {
        bindAddressRow(document);
    });

    document.addEventListener("securtek:formset-row-added", function (event) {
        if (event.detail && event.detail.row) {
            bindAddressRow(event.detail.row);
        }
    });

    window.SecurtekIndirizzi = {
        bindAddressRow: bindAddressRow,
        loadComuni: loadComuni,
    };
})();
