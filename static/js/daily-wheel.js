(function () {
    const i18n = window.TAROT_WHEEL_I18N;
    if (!i18n) return;

    const SEGMENTS = [20, 100, 50, 300, 30, 200];
    const fab = document.getElementById('dailyWheelFab');
    const badge = document.getElementById('dailyWheelBadge');
    const overlay = document.getElementById('dailyWheelModalOverlay');
    const closeBtn = document.getElementById('dailyWheelModalClose');
    const btn = document.getElementById('dailyWheelBtn');
    const labelEl = document.getElementById('dailyWheelLabel');
    if (!fab || !overlay || !btn || !labelEl) return;

    function polarOffset(angleDeg, radiusRatio, size) {
        const rad = (angleDeg - 90) * Math.PI / 180;
        const radius = size * radiusRatio;
        return { x: Math.cos(rad) * radius, y: Math.sin(rad) * radius };
    }

    let built = false;
    function buildWheelFace() {
        if (built) return;
        built = true;
        const size = btn.offsetWidth;
        const segCount = SEGMENTS.length;
        const angleStep = 360 / segCount;

        SEGMENTS.forEach((val, i) => {
            const center = angleStep * i + angleStep / 2;
            const pos = polarOffset(center, 0.31, size);
            const label = document.createElement('div');
            label.className = 'daily-wheel-seg-label';
            label.textContent = val;
            label.style.transform = `translate(${pos.x}px, ${pos.y}px)`;
            btn.appendChild(label);
        });

        for (let i = 0; i < segCount; i++) {
            const pos = polarOffset(angleStep * i, 0.475, size);
            const dot = document.createElement('div');
            dot.className = 'daily-wheel-dot';
            dot.style.transform = `translate(${pos.x}px, ${pos.y}px)`;
            btn.appendChild(dot);
        }

        const hub = document.createElement('div');
        hub.className = 'daily-wheel-hub';
        btn.appendChild(hub);
    }

    let spinning = false;
    let canSpin = true;

    function setState(spinAllowed) {
        canSpin = spinAllowed;
        btn.disabled = !spinAllowed;
        labelEl.textContent = spinAllowed ? i18n.spinLabel : i18n.comeBackLabel;
        badge.hidden = !spinAllowed;
    }

    function goToLogin() {
        window.location.href = i18n.loginUrl;
    }

    function showToast(amount) {
        const toast = document.createElement('div');
        toast.className = 'daily-wheel-toast';
        toast.textContent = `🎉 +${amount} ${i18n.jetonUnit}!`;
        document.body.appendChild(toast);
        setTimeout(() => toast.remove(), 3200);
    }

    function openModal() {
        overlay.hidden = false;
        buildWheelFace();
    }

    function closeModal() {
        overlay.hidden = true;
    }

    fab.addEventListener('click', () => {
        if (!i18n.loggedIn) { goToLogin(); return; }
        openModal();
    });
    closeBtn.addEventListener('click', closeModal);
    overlay.addEventListener('click', (e) => {
        if (e.target === overlay) closeModal();
    });

    btn.addEventListener('click', () => {
        if (spinning || btn.disabled) return;
        spinning = true;

        fetch('/api/gunluk-carki/cevir', { method: 'POST' })
            .then((r) => {
                if (r.status === 401) { goToLogin(); return null; }
                return r.json().then((d) => ({ status: r.status, body: d }));
            })
            .then((result) => {
                if (!result) { spinning = false; return; }
                const d = result.body;
                if (!d.ok) {
                    spinning = false;
                    setState(false);
                    return;
                }
                const segCount = SEGMENTS.length;
                const angleStep = 360 / segCount;
                const targetAngle = angleStep * d.index + angleStep / 2;
                const rotation = 6 * 360 - targetAngle;
                btn.style.transform = `rotate(${rotation}deg)`;
                setTimeout(() => {
                    spinning = false;
                    setState(false);
                    showToast(d.amount);
                    const balanceEl = document.getElementById('jetonBalance');
                    if (balanceEl && d.balance !== undefined) balanceEl.textContent = d.balance;
                }, 3700);
            })
            .catch(() => { spinning = false; });
    });

    function refreshStatus() {
        if (!i18n.loggedIn) { badge.hidden = true; return; }
        fetch('/api/gunluk-carki/durum')
            .then((r) => r.json())
            .then((d) => { if (d.ok) setState(d.can_spin); })
            .catch(() => {});
    }

    refreshStatus();
})();
