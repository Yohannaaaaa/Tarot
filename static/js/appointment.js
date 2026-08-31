(function () {
    const i18n = window.TAROT_APPT_I18N || {};
    const grid = document.getElementById('calGrid');
    const weekdaysEl = document.getElementById('calWeekdays');
    const monthLabel = document.getElementById('calMonthLabel');
    const prevBtn = document.getElementById('calPrev');
    const nextBtn = document.getElementById('calNext');
    const dateInput = document.getElementById('appointmentDateInput');
    const timeWrap = document.getElementById('timePickerWrap');
    const timeSelect = document.getElementById('appointmentTimeSelect');
    const form = document.getElementById('appointmentForm');

    if (!grid) return;

    let busyDates = new Set();
    const current = new Date();
    current.setDate(1);
    let selectedDateStr = null;

    function pad(n) { return n < 10 ? '0' + n : '' + n; }
    function toDateStr(y, m, d) { return `${y}-${pad(m + 1)}-${pad(d)}`; }

    (i18n.weekdays || []).forEach((label) => {
        const el = document.createElement('span');
        el.textContent = label;
        weekdaysEl.appendChild(el);
    });

    function updateHiddenInput() {
        if (selectedDateStr && timeSelect.value) {
            dateInput.value = `${selectedDateStr}T${timeSelect.value}`;
        }
    }

    function selectDate(dateStr, cell) {
        selectedDateStr = dateStr;
        document.querySelectorAll('.cal-day.cal-selected').forEach((el) => el.classList.remove('cal-selected'));
        cell.classList.add('cal-selected');
        timeWrap.hidden = false;
        updateHiddenInput();
    }

    function render() {
        const y = current.getFullYear();
        const m = current.getMonth();
        monthLabel.textContent = current.toLocaleDateString(i18n.locale || 'tr-TR', { month: 'long', year: 'numeric' });
        grid.innerHTML = '';

        const firstDay = new Date(y, m, 1);
        const startWeekday = (firstDay.getDay() + 6) % 7;
        const daysInMonth = new Date(y, m + 1, 0).getDate();
        const today = new Date();
        today.setHours(0, 0, 0, 0);

        for (let i = 0; i < startWeekday; i++) {
            const empty = document.createElement('span');
            empty.className = 'cal-day cal-empty';
            grid.appendChild(empty);
        }

        for (let d = 1; d <= daysInMonth; d++) {
            const dateStr = toDateStr(y, m, d);
            const cellDate = new Date(y, m, d);
            const cell = document.createElement('button');
            cell.type = 'button';
            cell.className = 'cal-day';
            cell.textContent = String(d);

            if (cellDate < today) {
                cell.classList.add('cal-past');
                cell.disabled = true;
            } else if (busyDates.has(dateStr)) {
                cell.classList.add('cal-busy');
                cell.textContent = '❌';
                cell.disabled = true;
            } else {
                cell.addEventListener('click', () => selectDate(dateStr, cell));
            }
            if (dateStr === selectedDateStr) cell.classList.add('cal-selected');
            grid.appendChild(cell);
        }
    }

    timeSelect.addEventListener('change', updateHiddenInput);
    prevBtn.addEventListener('click', () => { current.setMonth(current.getMonth() - 1); render(); });
    nextBtn.addEventListener('click', () => { current.setMonth(current.getMonth() + 1); render(); });

    if (form) {
        form.addEventListener('submit', (e) => {
            if (!dateInput.value) {
                e.preventDefault();
                alert(i18n.selectDatePrompt || 'Please select a date and time.');
            }
        });
    }

    fetch('/api/randevu/dolu-tarihler')
        .then((r) => r.json())
        .then((d) => {
            if (d.ok) busyDates = new Set(d.busy_dates);
        })
        .catch(() => {})
        .finally(render);
})();
