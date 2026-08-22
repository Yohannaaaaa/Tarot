(function () {
    const buttons = document.querySelectorAll('.spread-btn');
    const loading = document.getElementById('loading');
    const resultArea = document.getElementById('resultArea');
    const questionInput = document.getElementById('questionInput');
    const i18n = window.TAROT_I18N;

    function escapeHtml(str) {
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    function renderCard(entry) {
        const card = entry.card;
        const isReversed = card.orientation === 'reversed';
        const orientationLabel = isReversed ? i18n.reversed : i18n.upright;
        return `
        <div class="spread-slot">
            <span class="position-label">${escapeHtml(entry.position)}</span>
            <div class="spread-card">
                <img src="${card.image}" alt="${escapeHtml(card.name)}" class="${isReversed ? 'reversed-img' : ''}">
                <div>
                    <div class="spread-card-name">${escapeHtml(card.name)}</div>
                    <div class="spread-card-orientation">${escapeHtml(orientationLabel)}</div>
                    <p class="spread-card-intro">${escapeHtml(card.intro)}</p>
                </div>
            </div>
            <details class="spread-card-extra">
                <summary>+ ${escapeHtml(i18n.sections.symbols)} / ${escapeHtml(i18n.sections.questions)} / ${escapeHtml(i18n.sections.weekly)}</summary>
                <div class="extra-body">
                    <h5>${escapeHtml(i18n.sections.love)}</h5><p>${escapeHtml(card.love)}</p>
                    <h5>${escapeHtml(i18n.sections.career)}</h5><p>${escapeHtml(card.career)}</p>
                    <h5>${escapeHtml(i18n.sections.money)}</h5><p>${escapeHtml(card.money)}</p>
                    <h5>${escapeHtml(i18n.sections.health)}</h5><p>${escapeHtml(card.health)}</p>
                    <h5>${escapeHtml(i18n.sections.family)}</h5><p>${escapeHtml(card.family)}</p>
                    <h5>${escapeHtml(i18n.sections.symbols)}</h5><p>${escapeHtml(card.symbols)}</p>
                    <h5>${escapeHtml(i18n.sections.questions)}</h5><p>${escapeHtml(card.questions)}</p>
                    <h5>${escapeHtml(i18n.sections.weekly)}</h5><p>${escapeHtml(card.weekly)}</p>
                    <h5>${escapeHtml(i18n.sections.hidden)}</h5><p>${escapeHtml(card.hidden)}</p>
                </div>
            </details>
        </div>`;
    }

    function renderResult(data) {
        let html = '';
        if (data.question) {
            html += `<p class="reading-question">"${escapeHtml(data.question)}"</p>`;
        }
        html += `<h2 class="reading-name">${escapeHtml(data.name)}</h2>`;
        if (data.answer) {
            html += `<p class="reading-answer">${escapeHtml(data.answer)}</p>`;
        }
        html += '<div class="spread-grid">';
        data.spread.forEach((entry) => {
            html += renderCard(entry);
        });
        html += '</div>';
        html += `<div class="draw-again-wrap"><button class="btn btn-secondary" id="drawAgainBtn">🔄 ${escapeHtml(i18n.drawAgain)}</button></div>`;
        resultArea.innerHTML = html;

        const again = document.getElementById('drawAgainBtn');
        if (again) {
            again.addEventListener('click', () => draw(data.type));
        }
    }

    async function draw(spreadType) {
        loading.hidden = false;
        resultArea.innerHTML = '';
        try {
            const response = await fetch(`/api/tirage/${spreadType}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ question: questionInput.value.trim() }),
            });
            const data = await response.json();
            if (!data.ok) throw new Error(data.error || 'unknown error');
            renderResult(data);
        } catch (err) {
            resultArea.innerHTML = `<p class="reading-question">⚠️ ${escapeHtml(err.message)}</p>`;
        } finally {
            loading.hidden = true;
        }
    }

    buttons.forEach((btn) => {
        btn.addEventListener('click', () => draw(btn.dataset.spread));
    });
})();
