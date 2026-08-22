(function () {
    const buttons = document.querySelectorAll('#orientationToggle .toggle-btn');
    const panels = document.querySelectorAll('.orientation-panel');

    buttons.forEach((btn) => {
        btn.addEventListener('click', () => {
            const orientation = btn.dataset.orientation;
            buttons.forEach((b) => b.classList.toggle('active', b === btn));
            panels.forEach((p) => {
                p.hidden = p.dataset.panel !== orientation;
            });
        });
    });
})();
