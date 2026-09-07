(function () {
    function makeToggleButton() {
        var btn = document.createElement("button");
        btn.type = "button";
        btn.className = "password-toggle-btn";
        btn.setAttribute("aria-label", "Show/hide password");
        btn.tabIndex = -1;
        btn.textContent = "👁️";
        return btn;
    }

    function wrapField(input) {
        if (input.dataset.pwToggleReady) return;
        input.dataset.pwToggleReady = "1";

        var wrap = document.createElement("div");
        wrap.className = "password-field";
        input.parentNode.insertBefore(wrap, input);
        wrap.appendChild(input);

        var btn = makeToggleButton();
        wrap.appendChild(btn);

        btn.addEventListener("click", function () {
            var isHidden = input.type === "password";
            input.type = isHidden ? "text" : "password";
            btn.textContent = isHidden ? "🙈" : "👁️";
            btn.setAttribute("aria-pressed", isHidden ? "true" : "false");
        });
    }

    document.addEventListener("DOMContentLoaded", function () {
        document.querySelectorAll('input[type="password"]').forEach(wrapField);
    });
})();
