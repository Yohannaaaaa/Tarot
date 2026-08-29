(function () {
    const i18n = window.TAROT_I18N;
    const USERNAME_KEY = "rituams_username";

    function escapeHtml(str) {
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    // ---------- Username / jeton balance ----------
    const usernameInput = document.getElementById('usernameInput');
    const jetonBalanceEl = document.getElementById('jetonBalance');
    const bonusBtn = document.getElementById('bonusBtn');

    function getUsername() {
        return (usernameInput.value || '').trim();
    }

    usernameInput.value = localStorage.getItem(USERNAME_KEY) || '';

    function refreshBalance() {
        const username = getUsername();
        if (!username) {
            jetonBalanceEl.textContent = '—';
            return;
        }
        fetch(`/api/jeton?username=${encodeURIComponent(username)}`)
            .then((r) => r.json())
            .then((d) => {
                if (d.ok) jetonBalanceEl.textContent = d.balance;
            })
            .catch(() => {});
    }

    usernameInput.addEventListener('change', () => {
        localStorage.setItem(USERNAME_KEY, getUsername());
        refreshBalance();
    });

    bonusBtn.addEventListener('click', () => {
        const username = getUsername();
        if (!username) {
            alert(i18n.usernameRequired);
            return;
        }
        localStorage.setItem(USERNAME_KEY, username);
        fetch('/api/jeton/bonus', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username }),
        })
            .then((r) => r.json())
            .then((d) => {
                if (d.ok) {
                    jetonBalanceEl.textContent = d.balance;
                    alert(i18n.bonusSuccess);
                } else {
                    jetonBalanceEl.textContent = d.balance;
                    alert(i18n.bonusClaimed);
                }
            });
    });

    refreshBalance();

    // ---------- Tabs ----------
    const tabButtons = document.querySelectorAll('.tab-btn');
    const tabPanels = document.querySelectorAll('.tab-panel');
    tabButtons.forEach((btn) => {
        btn.addEventListener('click', () => {
            tabButtons.forEach((b) => b.classList.toggle('active', b === btn));
            tabPanels.forEach((p) => {
                p.hidden = p.dataset.panel !== btn.dataset.tab;
            });
        });
    });

    // ---------- Instant free card ----------
    const instantBtn = document.getElementById('instantBtn');
    const instantCard = document.getElementById('instantCard');
    const instantFront = document.getElementById('instantFront');
    const instantResult = document.getElementById('instantResult');

    if (instantBtn) {
        instantBtn.addEventListener('click', () => {
            fetch('/api/anlik')
                .then((r) => r.json())
                .then((d) => {
                    if (!d.ok) return;
                    const card = d.card;
                    instantCard.classList.remove('flipped');
                    instantFront.innerHTML = `<img src="${card.image}" alt="${escapeHtml(card.name)}"><div class="instant-name">${escapeHtml(card.name)}</div>`;
                    void instantCard.offsetWidth;
                    setTimeout(() => {
                        instantCard.classList.add('flipped');
                        instantResult.innerHTML = `<strong>${escapeHtml(card.name)}</strong> — ${escapeHtml(card.intro)}`;
                    }, 60);
                });
        });
    }

    // ---------- Spread readings ----------
    const spreadButtons = document.querySelectorAll('.spread-btn');
    const loading = document.getElementById('loading');
    const resultArea = document.getElementById('resultArea');
    const questionInput = document.getElementById('questionInput');

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
        const username = getUsername();
        if (!username) {
            alert(i18n.usernameRequired);
            return;
        }
        localStorage.setItem(USERNAME_KEY, username);
        loading.hidden = false;
        resultArea.innerHTML = '';
        try {
            const response = await fetch(`/api/tirage/${spreadType}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ question: questionInput.value.trim(), username }),
            });
            const data = await response.json();
            if (response.status === 402) {
                resultArea.innerHTML = `<p class="reading-question">💰 ${escapeHtml(i18n.jetonInsufficient)} (${data.balance}/${data.cost} ${escapeHtml(i18n.jetonUnit)})</p>`;
                return;
            }
            if (!data.ok) throw new Error(data.error || 'unknown error');
            jetonBalanceEl.textContent = data.remaining_jeton;
            renderResult(data);
        } catch (err) {
            resultArea.innerHTML = `<p class="reading-question">⚠️ ${escapeHtml(err.message)}</p>`;
        } finally {
            loading.hidden = true;
        }
    }

    spreadButtons.forEach((btn) => {
        btn.addEventListener('click', () => draw(btn.dataset.spread));
    });

    // ---------- Services / rituals "select & send" ----------
    const contactForm = document.getElementById('contactForm');
    const formStatus = document.getElementById('formStatus');

    document.querySelectorAll('.btn-select:not(.btn-buy-pack)').forEach((btn) => {
        btn.addEventListener('click', () => {
            document.getElementById('fCategory').value = btn.dataset.category;
            document.getElementById('fService').value = btn.dataset.name;
            document.getElementById('fCost').value = btn.dataset.cost;
            contactForm.scrollIntoView({ behavior: 'smooth', block: 'start' });
            formStatus.textContent = `${btn.dataset.name} — 🪙 ${btn.dataset.cost}`;
        });
    });

    // ---------- Jeton pack purchase (Stripe Checkout) ----------
    document.querySelectorAll('.btn-buy-pack').forEach((btn) => {
        btn.addEventListener('click', () => {
            const username = getUsername();
            if (!username) {
                alert(i18n.usernameRequired);
                return;
            }
            localStorage.setItem(USERNAME_KEY, username);
            const amount = parseInt(btn.dataset.amount, 10);
            btn.disabled = true;
            fetch('/api/jeton/checkout', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, amount }),
            })
                .then((r) => r.json())
                .then((d) => {
                    if (d.ok && d.url) {
                        window.location.href = d.url;
                    } else {
                        alert(i18n.buyPackError);
                        btn.disabled = false;
                    }
                })
                .catch(() => {
                    alert(i18n.buyPackError);
                    btn.disabled = false;
                });
        });
    });

    if (contactForm) {
        contactForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const name = document.getElementById('fName').value.trim();
            const email = document.getElementById('fEmail').value.trim();
            const question = document.getElementById('fQuestion').value.trim();
            if (!name || !email || !question) {
                formStatus.textContent = i18n.formNeedFields;
                return;
            }
            formStatus.textContent = i18n.formSending;
            fetch('/api/mesaj', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    name,
                    email,
                    question,
                    motherName: document.getElementById('fMother').value.trim(),
                    birthDate: document.getElementById('fBirth').value,
                    responseType: document.getElementById('fResponseType').value,
                    appointmentDate: document.getElementById('fAppointment').value,
                    category: document.getElementById('fCategory').value,
                    service: document.getElementById('fService').value,
                    cost: document.getElementById('fCost').value,
                }),
            })
                .then((r) => r.json())
                .then((d) => {
                    formStatus.textContent = d.ok ? i18n.formSuccess : i18n.formError;
                    if (d.ok) contactForm.reset();
                })
                .catch(() => {
                    formStatus.textContent = i18n.formError;
                });
        });
    }
})();
