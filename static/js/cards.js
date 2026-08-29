(function () {
    const search = document.getElementById('cardSearch');
    const chips = document.querySelectorAll('.chip');
    const tiles = document.querySelectorAll('.card-tile');
    const noResults = document.getElementById('noResults');
    let activeFilter = 'all';

    function apply() {
        const q = (search.value || '').trim().toLowerCase();
        let visible = 0;
        tiles.forEach((tile) => {
            const matchesText = !q || tile.dataset.name.includes(q);
            const matchesFilter =
                activeFilter === 'all' ||
                (activeFilter === 'major' && tile.dataset.arcana === 'major') ||
                tile.dataset.suit === activeFilter;
            const show = matchesText && matchesFilter;
            tile.style.display = show ? '' : 'none';
            if (show) visible += 1;
        });
        noResults.hidden = visible !== 0;
    }

    search.addEventListener('input', apply);
    chips.forEach((chip) => {
        chip.addEventListener('click', () => {
            chips.forEach((c) => c.classList.remove('active'));
            chip.classList.add('active');
            activeFilter = chip.dataset.filter;
            apply();
        });
    });
})();
