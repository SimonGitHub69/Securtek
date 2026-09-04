(function () {
    "use strict";

    var HOLD_MAX_MS = 2500;
    var APPLY_TIMES = [0, 16, 50, 100, 200, 400];

    var SECTION_MAP = {
        personale: ["practice-technicians-section", "pratica-form-personale-section"],
        agenda: ["practice-agenda-section"],
        categorie: ["practice-categories-section", "pratica-form-categorie-section"],
        comunicazioni: ["practice-communications-section"],
    };

    function readScrollTarget() {
        var fromAttr = document.documentElement.getAttribute("data-scroll-y");
        if (fromAttr !== null && fromAttr !== "") {
            var attrValue = parseInt(fromAttr, 10);
            if (!isNaN(attrValue) && attrValue >= 0) {
                return attrValue;
            }
        }
        try {
            var fromQuery = new URLSearchParams(window.location.search).get("scroll");
            if (fromQuery !== null && fromQuery !== "") {
                var queryValue = parseInt(fromQuery, 10);
                if (!isNaN(queryValue) && queryValue >= 0) {
                    return queryValue;
                }
            }
        } catch (error) {
            /* ignore */
        }
        return null;
    }

    function focusSectionName() {
        var fromAttr = document.documentElement.getAttribute("data-focus-section");
        if (fromAttr) {
            return fromAttr;
        }
        if (document.documentElement.getAttribute("data-focus-personale") === "1") {
            return "personale";
        }
        try {
            var params = new URLSearchParams(window.location.search);
            var pos = params.get("pos") || params.get("focus");
            if (pos && SECTION_MAP[pos]) {
                return pos;
            }
        } catch (error) {
            /* ignore */
        }
        return null;
    }

    function expandSection(name) {
        var ids = SECTION_MAP[name] || [];
        ids.forEach(function (id) {
            var section = document.getElementById(id);
            var toggle = document.querySelector(
                '.st-collapse-toggle[data-collapse-target="' + id + '"]'
            );
            if (!section) {
                return;
            }
            section.hidden = false;
            if (toggle) {
                toggle.classList.remove("is-collapsed");
                toggle.setAttribute("aria-expanded", "true");
                toggle.title = "Comprimi sezione";
            }
            document
                .querySelectorAll('.st-section-header[data-collapse-target="' + id + '"]')
                .forEach(function (header) {
                    header.classList.remove("is-collapsed");
                });
            try {
                if (toggle && toggle.dataset.storageKey) {
                    localStorage.setItem(toggle.dataset.storageKey, "0");
                }
            } catch (error) {
                /* ignore */
            }
        });
    }

    function applyScroll(top) {
        var y = Math.max(0, Math.round(top || 0));
        if (typeof window.scrollTo === "function") {
            window.scrollTo(0, y);
        }
        document.documentElement.scrollTop = y;
        document.body.scrollTop = y;
    }

    function cleanUrl() {
        try {
            var url = new URL(window.location.href);
            var changed = false;
            ["scroll", "pos", "focus"].forEach(function (key) {
                if (url.searchParams.has(key)) {
                    url.searchParams.delete(key);
                    changed = true;
                }
            });
            if (url.hash === "#agenda" || url.hash === "#categorie" || url.hash === "#personale" || url.hash === "#comunicazioni") {
                url.hash = "";
                changed = true;
            }
            if (changed) {
                var next =
                    url.pathname +
                    (url.searchParams.toString() ? "?" + url.searchParams.toString() : "");
                window.history.replaceState(null, "", next);
            }
        } catch (error) {
            /* ignore */
        }
    }

    function release() {
        document.documentElement.classList.remove("st-hold-scroll");
        document.documentElement.removeAttribute("data-scroll-y");
        document.documentElement.removeAttribute("data-focus-personale");
        document.documentElement.removeAttribute("data-focus-section");
    }

    function restore() {
        var section = focusSectionName();
        var top = readScrollTarget();

        // Hash legacy (#agenda): non scrollare all'ancora, solo espandi e tieni posizione.
        if (top === null && !section) {
            try {
                var hash = (window.location.hash || "").replace("#", "");
                if (SECTION_MAP[hash]) {
                    section = hash;
                }
            } catch (error) {
                /* ignore */
            }
        }

        if (top === null && !section) {
            release();
            return false;
        }

        if (section) {
            expandSection(section);
        }

        if (top === null) {
            // Senza ?scroll= riporta comunque alla sezione (es. Personale).
            var sectionTarget = null;
            if (section === "personale") {
                sectionTarget = document.getElementById("personale");
            } else if (section === "agenda") {
                sectionTarget = document.getElementById("agenda");
            } else if (section === "categorie") {
                sectionTarget = document.getElementById("categorie");
            } else if (section === "comunicazioni") {
                sectionTarget = document.getElementById("comunicazioni");
            }
            if (!sectionTarget && section) {
                var ids = SECTION_MAP[section] || [];
                for (var i = 0; i < ids.length; i += 1) {
                    sectionTarget = document.getElementById(ids[i]);
                    if (sectionTarget) {
                        break;
                    }
                }
            }
            if (sectionTarget && typeof sectionTarget.scrollIntoView === "function") {
                window.setTimeout(function () {
                    sectionTarget.scrollIntoView({ block: "start" });
                }, 0);
            }
            cleanUrl();
            release();
            return true;
        }

        var released = false;
        function finish() {
            if (released) {
                return;
            }
            released = true;
            applyScroll(top);
            cleanUrl();
            release();
        }

        APPLY_TIMES.forEach(function (delay) {
            window.setTimeout(function () {
                applyScroll(top);
                if (delay >= 200) {
                    finish();
                }
            }, delay);
        });

        window.addEventListener("load", function () {
            applyScroll(top);
            finish();
        });

        window.setTimeout(finish, HOLD_MAX_MS);
        return true;
    }

    function currentScrollY() {
        return (
            window.scrollY ||
            window.pageYOffset ||
            document.documentElement.scrollTop ||
            document.body.scrollTop ||
            0
        );
    }

    function withScrollInUrl(url, scrollY) {
        try {
            var absolute = new URL(url, window.location.origin);
            if (absolute.origin !== window.location.origin) {
                return url;
            }
            absolute.searchParams.set("scroll", String(Math.max(0, Math.round(scrollY || 0))));
            absolute.hash = "";
            return absolute.pathname + absolute.search;
        } catch (error) {
            return url;
        }
    }

    function linkReturnKind(url) {
        var path = url.pathname || "";
        if (path.indexOf("/tecnici/") !== -1) {
            return "personale";
        }
        // Personale anagrafica: /anagrafiche/<id>/personale/...
        if (path.indexOf("/personale/") !== -1) {
            return "personale";
        }
        if (path.indexOf("/comunicazioni/") !== -1) {
            return "comunicazioni";
        }
        if (path.indexOf("/categorie/") !== -1 || path.indexOf("/categoria") !== -1) {
            return "categorie";
        }
        // /agenda/nuovo/ oppure /agenda/<id>/modifica/
        if (path.indexOf("/agenda/") !== -1) {
            if (
                path.indexOf("/nuovo") !== -1 ||
                path.indexOf("/modifica") !== -1 ||
                /\/agenda\/\d+\//.test(path)
            ) {
                return "agenda";
            }
        }
        return null;
    }

    function enrichReturnLink(link) {
        if (!link || !link.href) {
            return;
        }
        try {
            var url = new URL(link.href, window.location.origin);
            if (url.origin !== window.location.origin) {
                return;
            }
            var kind = linkReturnKind(url);
            if (!kind) {
                return;
            }
            var nextValue =
                url.searchParams.get("next") ||
                window.location.pathname + window.location.search;
            var nextUrl = new URL(nextValue, window.location.origin);
            nextUrl.hash = "";
            nextUrl.searchParams.set("scroll", String(currentScrollY()));
            nextUrl.searchParams.set("pos", kind);
            url.searchParams.set("next", nextUrl.pathname + nextUrl.search);
            var href = url.pathname + url.search;
            link.href = href;
            link.setAttribute("href", href);
        } catch (error) {
            /* ignore */
        }
    }

    function captureScrollOnForms() {
        document.querySelectorAll("form[method='post']").forEach(function (form) {
            if (form.dataset.scrollCapture === "1") {
                return;
            }
            form.dataset.scrollCapture = "1";
            form.addEventListener("submit", function () {
                var field = form.querySelector('input[name="scroll_y"]');
                if (!field) {
                    field = document.createElement("input");
                    field.type = "hidden";
                    field.name = "scroll_y";
                    form.appendChild(field);
                }
                var scrollValue = currentScrollY();
                var nextField = form.querySelector('input[name="next"]');
                if (nextField && nextField.value) {
                    try {
                        var nextUrl = new URL(nextField.value, window.location.origin);
                        nextUrl.hash = "";
                        var fromNext = nextUrl.searchParams.get("scroll");
                        if (fromNext !== null && fromNext !== "") {
                            var parsed = parseInt(fromNext, 10);
                            if (!isNaN(parsed) && parsed >= 0) {
                                scrollValue = parsed;
                            }
                        }
                        nextField.value = nextUrl.pathname + nextUrl.search;
                    } catch (error) {
                        /* ignore */
                    }
                }
                field.value = String(Math.max(0, Math.round(scrollValue)));
            });
        });
    }

    function captureScrollOnDeleteForms() {
        document.querySelectorAll("#deleteTecnicoForm, #deleteCategoryForm").forEach(function (form) {
            if (form.dataset.scrollDeleteCapture === "1") {
                return;
            }
            form.dataset.scrollDeleteCapture = "1";
            form.addEventListener("submit", function () {
                var nextField = form.querySelector('input[name="next"]');
                if (!nextField) {
                    nextField = document.createElement("input");
                    nextField.type = "hidden";
                    nextField.name = "next";
                    form.appendChild(nextField);
                }
                var base = nextField.value || window.location.pathname + window.location.search;
                var pos =
                    form.id === "deleteCategoryForm"
                        ? "categorie"
                        : "personale";
                nextField.value = withScrollInUrl(base, currentScrollY());
                try {
                    var u = new URL(nextField.value, window.location.origin);
                    u.searchParams.set("pos", pos);
                    u.hash = "";
                    nextField.value = u.pathname + u.search;
                } catch (error) {
                    /* ignore */
                }
            });
        });
    }

    // Registrazione immediata (prima di embed.js): aggiorna next+scroll sul click.
    document.addEventListener(
        "click",
        function (event) {
            var link = event.target.closest("a[href]");
            if (link) {
                enrichReturnLink(link);
            }
        },
        true
    );

    window.SecurtekScrollHold = {
        restore: restore,
        release: release,
        currentScrollY: currentScrollY,
        withScrollInUrl: withScrollInUrl,
        enrichReturnLink: enrichReturnLink,
        enrichTecnicoLink: enrichReturnLink,
        expandPersonaleSection: function () {
            expandSection("personale");
        },
        expandSection: expandSection,
    };

    function boot() {
        restore();
        captureScrollOnForms();
        captureScrollOnDeleteForms();
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", boot);
    } else {
        boot();
    }
})();
