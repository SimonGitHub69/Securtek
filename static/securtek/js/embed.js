(function () {
    "use strict";

    if (!document.body.classList.contains("st-embed")) {
        return;
    }

    function addEmbed(url) {
        try {
            var u = new URL(url, window.location.origin);
            if (u.origin !== window.location.origin) {
                return url;
            }
            u.searchParams.set("embed", "1");
            return u.pathname + u.search + u.hash;
        } catch (e) {
            return url;
        }
    }

    document.addEventListener(
        "click",
        function (ev) {
            if (ev.defaultPrevented || ev.button !== 0) {
                return;
            }
            if (ev.metaKey || ev.ctrlKey || ev.shiftKey || ev.altKey) {
                return;
            }
            var link = ev.target.closest("a[href]");
            if (!link) {
                return;
            }
            var raw = link.getAttribute("href");
            if (!raw || raw.charAt(0) === "#" || raw.indexOf("javascript:") === 0) {
                return;
            }
            try {
                // Usa link.href (può essere già arricchito da scroll-hold con next+scroll).
                var live = link.href || raw;
                var u = new URL(live, window.location.origin);
                if (u.origin !== window.location.origin) {
                    return;
                }
                if (u.searchParams.get("embed") === "1") {
                    return;
                }
                var nextHref = addEmbed(live);
                link.href = nextHref;
                link.setAttribute("href", nextHref);
                // Lascia navigare il browser: niente preventDefault, così non
                // si perde lo scroll messo in next da scroll-hold.
            } catch (e) {
                /* ignore */
            }
        },
        true
    );

    document.addEventListener(
        "submit",
        function (ev) {
            var form = ev.target;
            if (!form || form.tagName !== "FORM") {
                return;
            }
            var method = (form.getAttribute("method") || "get").toLowerCase();
            if (method === "get") {
                var action = form.getAttribute("action") || window.location.href;
                form.setAttribute("action", addEmbed(action));
                if (!form.querySelector('input[name="embed"]')) {
                    var input = document.createElement("input");
                    input.type = "hidden";
                    input.name = "embed";
                    input.value = "1";
                    form.appendChild(input);
                }
            } else if (!form.querySelector('input[name="embed"]')) {
                var hidden = document.createElement("input");
                hidden.type = "hidden";
                hidden.name = "embed";
                hidden.value = "1";
                form.appendChild(hidden);
            }
        },
        true
    );
})();
