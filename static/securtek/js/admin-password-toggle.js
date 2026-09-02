(function () {
    "use strict";

    var ICON_SHOW =
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' +
        '<path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12Z"></path>' +
        '<circle cx="12" cy="12" r="3"></circle>' +
        "</svg>";

    var ICON_HIDE =
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' +
        '<path d="M3 3l18 18"></path>' +
        '<path d="M10.6 10.6a3 3 0 0 0 4.2 4.2"></path>' +
        '<path d="M9.9 5.1A11 11 0 0 1 12 5c6.5 0 10 7 10 7a18 18 0 0 1-3.2 3.8"></path>' +
        '<path d="M6.1 6.1A18 18 0 0 0 2 12s3.5 7 10 7a11 11 0 0 0 4.2-.8"></path>' +
        "</svg>";

    function enhance(input) {
        if (!input || input.dataset.stPwToggle === "1") {
            return;
        }
        if ((input.getAttribute("type") || "").toLowerCase() !== "password") {
            return;
        }
        if (input.closest(".st-pw-wrap")) {
            input.dataset.stPwToggle = "1";
            return;
        }

        input.dataset.stPwToggle = "1";

        var wrap = document.createElement("div");
        wrap.className = "st-pw-wrap";
        input.parentNode.insertBefore(wrap, input);
        wrap.appendChild(input);

        var btn = document.createElement("button");
        btn.type = "button";
        btn.className = "st-pw-toggle";
        btn.setAttribute("aria-label", "Mostra password");
        btn.setAttribute("title", "Mostra password");
        btn.setAttribute("aria-pressed", "false");
        btn.innerHTML = ICON_SHOW;

        btn.addEventListener("click", function () {
            var visible = input.getAttribute("type") === "text";
            input.setAttribute("type", visible ? "password" : "text");
            btn.setAttribute("aria-pressed", visible ? "false" : "true");
            btn.setAttribute("aria-label", visible ? "Mostra password" : "Nascondi password");
            btn.setAttribute("title", visible ? "Mostra password" : "Nascondi password");
            btn.innerHTML = visible ? ICON_SHOW : ICON_HIDE;
            btn.classList.toggle("is-visible", !visible);
            input.focus();
        });

        wrap.appendChild(btn);
    }

    function scan(root) {
        var scope = root && root.querySelectorAll ? root : document;
        scope.querySelectorAll('input[type="password"]').forEach(enhance);
        if (scope.matches && scope.matches('input[type="password"]')) {
            enhance(scope);
        }
    }

    function init() {
        scan(document);

        if (typeof MutationObserver === "undefined" || !document.body) {
            return;
        }

        var observer = new MutationObserver(function (mutations) {
            mutations.forEach(function (mutation) {
                mutation.addedNodes.forEach(function (node) {
                    if (node.nodeType === 1) {
                        scan(node);
                    }
                });
            });
        });

        observer.observe(document.body, { childList: true, subtree: true });
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
})();
