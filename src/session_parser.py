from datetime import datetime, timedelta
import hashlib
import re
from zoneinfo import ZoneInfo
from bs4 import BeautifulSoup
from src.models import (
    LessonEvent,
    SemesterConfig,
    format_teacher_initials,
    get_default_config,
)

_MONTHS = {
    "января": 1, "февраля": 2, "марта": 3, "апреля": 4, "мая": 5, "июня": 6,
    "июля": 7, "августа": 8, "сентября": 9, "октября": 10, "ноября": 11, "декабря": 12,
}


def parse_session_table(html_content: str, config: SemesterConfig = None) -> list[LessonEvent]:
    config = config or get_default_config()
    tz = ZoneInfo(config.timezone)
    soup = BeautifulSoup(html_content, "html.parser")
    table = None
    for h in soup.find_all(["h1", "h2", "h3", "h4", "p", "div"]):
        if "расписание сессии" in h.get_text().lower():
            table = h.find_next("table")
            break
    if not table:
        return []

    events: list[LessonEvent] = []
    for tr in table.find_all("tr"):
        cells = [c.get_text(" ", strip=True) for c in tr.find_all(["td", "th"])]
        if len(cells) < 3:
            continue
        m_date = re.search(r"(\d{1,2})\s+([а-яёА-ЯЁ]+)\s+(\d{4})", cells[0])
        m_time = re.findall(r"(\d{1,2})[.:](\d{2})", cells[1])
        if not m_date or not m_time:
            continue
        d, m_name, y = int(m_date.group(1)), m_date.group(2).lower(), int(m_date.group(3))
        if m_name not in _MONTHS:
            continue
        s_dt = datetime(y, _MONTHS[m_name], d, int(m_time[0][0]), int(m_time[0][1]), tzinfo=tz)
        e_dt = datetime(y, _MONTHS[m_name], d, int(m_time[1][0]), int(m_time[1][1]), tzinfo=tz) if len(m_time) > 1 else s_dt + timedelta(minutes=90)

        info = cells[2]
        m_type = re.search(r"\(([^)]+)\)\s*$", info)
        raw_type = m_type.group(1).strip().lower() if m_type else ""
        lesson_type = "конс." if "конс" in raw_type else ("экз." if "экз" in raw_type else raw_type)
        rem = info[:m_type.start()].strip() if m_type else info.strip()
        subj, raw_teacher = rem.rsplit(",", 1) if "," in rem else (rem, "")
        summary = subj.strip(" \"'«»")
        loc, t_full, t_title = format_teacher_initials(raw_teacher)
        t_name = f"{t_title} {t_full}".strip() if t_title else t_full
        t_line = f"{t_name} ({lesson_type})".strip() if lesson_type else t_name
        desc = f"Предмет: {summary}\nВремя: {s_dt.strftime('%H:%M')} - {e_dt.strftime('%H:%M')}\nПреподаватель: {t_line}"
        uid = f"session-{hashlib.sha256(f'{summary}_{s_dt.isoformat()}_{lesson_type}'.encode()).hexdigest()[:16]}@nspu"

        events.append(LessonEvent(
            summary=summary, location=loc, description=desc, start_dt=s_dt, end_dt=e_dt,
            teacher_full=t_full, teacher_short=loc, teacher_title=t_title, lesson_type=lesson_type,
            is_session=True, uid=uid,
        ))
    return events


def parse_schedule_html(html_content: str, config: SemesterConfig = None) -> list[LessonEvent]:
    config = config or get_default_config()
    events = list(parse_session_table(html_content, config))
    try:
        from src.grid_parser import parse_main_grid
        events.extend(parse_main_grid(html_content, config))
    except (ImportError, AttributeError):
        pass
    events.sort(key=lambda ev: ev.start_dt)
    return events
