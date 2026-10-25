function getTypeClass(type = '') {
  const t = type.toLowerCase();
  if (t.includes('лек') || t.includes('л.')) return 'type-lec';
  if (t.includes('прак') || t.includes('пр.')) return 'type-prac';
  return 'type-exam';
}

function renderEvents(events, week, day) {
  const container = document.getElementById('schedule-container');
  if (!container) return;
  const list = (events || []).filter(e => {
    const matchWeek = week === 'session' ? e.is_session : (String(e.week_number) === String(week) && !e.is_session);
    const matchDay = day === 'all' || !day || (e.day_of_week && e.day_of_week.toLowerCase().startsWith(day.toLowerCase()));
    return matchWeek && matchDay;
  });
  if (!list.length) {
    container.innerHTML = '<div class="loading">Занятий не найдено</div>';
    return;
  }
  container.innerHTML = list.map(e => `
    <article class="card">
      <div class="card-header">
        <span class="lesson-time">${e.time || ''}</span>
        <span class="lesson-type ${getTypeClass(e.type)}">${e.type || 'Занятие'}</span>
      </div>
      <h3 class="lesson-title">${e.summary || ''}</h3>
      <div class="lesson-meta">
        <span>👨‍🏫 ${e.teacher || e.location || 'Преподаватель не указан'}</span>
        ${e.date ? `<span>📅 ${e.date} (${e.day_of_week || ''})</span>` : ''}
      </div>
    </article>
  `).join('');
}

async function loadSchedule() {
  if (window.SCHEDULE_DATA) return window.SCHEDULE_DATA;
  try {
    const res = await fetch('events.json');
    if (res.ok) return await res.json();
  } catch (e) { console.warn('Using fallback data', e); }
  return { events: [] };
}

document.addEventListener('DOMContentLoaded', async () => {
  const data = await loadSchedule();
  const weekSelect = document.getElementById('week-select');
  if (weekSelect && !weekSelect.options.length) {
    for (let i = 1; i <= 13; i++) weekSelect.add(new Option(`Неделя ${i}`, String(i)));
    weekSelect.add(new Option('Экзаменационная сессия', 'session'));
  }
  let currentDay = 'all';
  const update = () => renderEvents(data.events, weekSelect ? weekSelect.value : '1', currentDay);

  if (weekSelect) weekSelect.addEventListener('change', update);
  document.querySelectorAll('#days-filter .day-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('#days-filter .day-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      currentDay = btn.dataset.day || 'all';
      update();
    });
  });

  const icsPath = 'schedule-nspu.ics';
  const icsUrl = new URL(icsPath, window.location.href).href;
  const webcalUrl = icsUrl.replace(/^https?:\/\//i, 'webcal://');
  const btnApple = document.getElementById('btn-apple');
  if (btnApple) btnApple.href = webcalUrl;
  const btnGoogle = document.getElementById('btn-google');
  if (btnGoogle) btnGoogle.href = `https://calendar.google.com/calendar/render?cid=${encodeURIComponent(webcalUrl)}`;
  const btnDownload = document.getElementById('btn-download');
  if (btnDownload) btnDownload.href = icsPath;
  const btnCopy = document.getElementById('btn-copy');
  if (btnCopy) {
    btnCopy.addEventListener('click', async () => {
      try { await navigator.clipboard.writeText(icsUrl); } catch {
        const ta = document.createElement('textarea');
        ta.value = icsUrl; document.body.appendChild(ta); ta.select(); document.execCommand('copy'); ta.remove();
      }
      const toast = document.getElementById('toast');
      if (toast) {
        toast.classList.add('show');
        setTimeout(() => toast.classList.remove('show'), 2500);
      }
    });
  }
  update();
});