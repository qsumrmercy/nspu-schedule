from datetime import datetime, time
import hashlib
import re
from urllib.parse import parse_qs
from zoneinfo import ZoneInfo
from bs4 import BeautifulSoup
from src.models import (
    LessonEvent, SemesterConfig, calculate_dates_for_weeks,
    format_teacher_initials, get_default_config,
)

DAYS = {'понедельник': 0, 'вторник': 1, 'среда': 2, 'четверг': 3, 'пятница': 4, 'суббота': 5}
TYPES = {0: 'л.', 1: 'п.з.', 2: 'л.з.'}


def _parse_weeks(token: str) -> list[int]:
    weeks = []
    for p in token.split(','):
        p = p.strip()
        if '-' in p:
            s, e = p.split('-')
            weeks.extend(range(int(s), int(e) + 1))
        elif p.isdigit():
            weeks.append(int(p))
    return weeks


def _get_title(td, prep: str) -> str:
    last = prep.split()[0] if prep else ''
    for tl in td.find_all('a', href=re.compile(r'teacher_shedule\.php')):
        if last and last in tl.get_text() and tl.previous_sibling:
            m = re.search(r'(доц\.?|проф\.?|ст\.?\s*преп\.?|преп\.?|асс\.?)', str(tl.previous_sibling))
            if m:
                return m.group(0).strip()
    return ''


def parse_main_grid(html_content: str, config: SemesterConfig | None = None) -> list[LessonEvent]:
    """Парсинг регулярной сетки пар НГПУ."""
    cfg = config or get_default_config()
    tz = ZoneInfo(cfg.timezone)
    cleaned = re.sub(r'<tr>\s*</td>\s*</tr>', '', html_content)
    soup = BeautifulSoup(cleaned, 'html.parser')

    grid = next((t for t in soup.find_all('table', class_='rasp_table')
                 if 'понедельник' in t.get_text().lower() and 'вторник' in t.get_text().lower()), None)
    if not grid:
        return []

    events: list[LessonEvent] = []
    day_idx = None
    for tr in grid.find_all('tr'):
        tds = tr.find_all('td')
        if not tds:
            continue
        first_txt = tds[0].get_text(strip=True).lower()
        if first_txt in DAYS:
            day_idx, time_cell, content = DAYS[first_txt], tds[1].get_text(strip=True), tds[2:]
        else:
            time_cell, content = tds[0].get_text(strip=True), tds[1:]

        tm = re.search(r'(\d{1,2})[:.](\d{2})\s*[-–]\s*(\d{1,2})[:.](\d{2})', time_cell)
        if not tm or day_idx is None:
            continue
        t_start = time(int(tm.group(1)), int(tm.group(2)))
        t_end = time(int(tm.group(3)), int(tm.group(4)))
        t_str = f"{tm.group(1).zfill(2)}:{tm.group(2)} - {tm.group(3).zfill(2)}:{tm.group(4)}"

        col = 0
        for td in content:
            cp = int(td.get('colspan', 1))
            for a in td.find_all('a', href=re.compile(r'group_shedule_weeks\.php')):
                qs = parse_qs(a.get('href', '').split('?')[-1])
                pred, prep = qs.get('pred', [''])[0].strip(), qs.get('prep', [''])[0].strip()
                weeks_raw, fancy = qs.get('weeks', [''])[0], qs.get('fancy', [''])[0]
                short_name, full_name, t_init = format_teacher_initials(prep)
                title = _get_title(td, prep) or t_init

                parts = weeks_raw.split('|')
                items = [(TYPES.get(i, 'зан.'), _parse_weeks(tk)) for i, tk in enumerate(parts[:3]) if tk.strip()]
                if not items:
                    lt = next((k for k in ('л.з.', 'п.з.', 'л.') if k in fancy), 'зан.')
                    items = [(lt, _parse_weeks(weeks_raw))]

                teacher_desc = f"{title} {full_name}".strip()
                desc = f"Предмет: {pred}\nВремя: {t_str}\nПреподаватель: {teacher_desc}"
                for l_type, w_nums in items:
                    filtered = [w for w in w_nums if (w % 2 == 1 if col == 0 else w % 2 == 0)] if cp == 1 else w_nums
                    for dt in calculate_dates_for_weeks(day_idx, filtered, cfg):
                        s_dt, e_dt = datetime.combine(dt, t_start, tzinfo=tz), datetime.combine(dt, t_end, tzinfo=tz)
                        uid = hashlib.sha256(f"{pred}_{s_dt.isoformat()}_{short_name}_{l_type}".encode()).hexdigest()
                        events.append(LessonEvent(pred, short_name, desc, s_dt, e_dt, full_name, short_name, title, l_type, False, uid))
            col += cp

    events.sort(key=lambda ev: (ev.start_dt, ev.summary))
    return events
