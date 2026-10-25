from dataclasses import dataclass
from datetime import date, datetime, timedelta
import re


@dataclass(frozen=True)
class LessonEvent:
    """Нормализованное занятие / мероприятие в расписании."""
    summary: str
    location: str
    description: str
    start_dt: datetime
    end_dt: datetime
    teacher_full: str
    teacher_short: str
    teacher_title: str
    lesson_type: str
    is_session: bool
    uid: str


@dataclass(frozen=True)
class SemesterConfig:
    """Конфигурация семестра и таймзоны."""
    start_date: date = date(2026, 9, 1)
    end_date: date = date(2026, 11, 23)
    week1_monday: date = date(2026, 8, 31)
    timezone: str = "Asia/Novosibirsk"
    session_start: date = date(2026, 11, 24)
    session_end: date = date(2026, 11, 27)


def get_default_config() -> SemesterConfig:
    """Возвращает стандартную конфигурацию семестра 2026."""
    return SemesterConfig()


def calculate_dates_for_weeks(
    day_of_week: int,
    weeks: list[int],
    config: SemesterConfig,
) -> list[date]:
    """Вычисляет список дат для дня недели (0=Пн .. 5=Сб) и номеров недель."""
    dates: list[date] = []
    for w in sorted(set(weeks)):
        d = config.week1_monday + timedelta(days=(w - 1) * 7 + day_of_week)
        if config.start_date <= d <= config.end_date:
            dates.append(d)
    return dates


_TITLE_PATTERN = re.compile(
    r'^(?:(?i:доц\.?|доцент|проф\.?|профессор|ст\.?\s*преп\.?|преп\.?|преподаватель|асс\.?|ассистент)\s*|д\.\s+)'
)
_INIT_FIRST_PATTERN = re.compile(
    r'^([А-ЯЁA-Z])\s*\.\s*(?:([А-ЯЁA-Z])\s*\.\s*)?([А-ЯЁа-яёA-Za-z\-]+)$'
)
_LAST_FIRST_PATTERN = re.compile(
    r'^([А-ЯЁа-яёA-Za-z\-]+)\s+([А-ЯЁA-Z])\s*\.\s*(?:([А-ЯЁA-Z])\s*\.)?$'
)


def format_teacher_initials(teacher_str: str) -> tuple[str, str, str]:
    """Парсит строку преподавателя и возвращает (short_name, full_name, title)."""
    if not teacher_str or not teacher_str.strip():
        return ("", "", "")

    s = teacher_str.strip()
    m_title = _TITLE_PATTERN.match(s)
    title = ""
    if m_title:
        title = m_title.group(0).strip()
        s = s[m_title.end():].strip()

    full_name = s
    short_name = s

    # 1. Инициалы впереди: 'Д.В.Чернов', 'Д.В. Чернов', 'Д. Чернов'
    m_init = _INIT_FIRST_PATTERN.match(s)
    if m_init:
        i1, i2, last = m_init.group(1), m_init.group(2), m_init.group(3)
        short_name = f"{i1.upper()}.{i2.upper()}. {last}" if i2 else f"{i1.upper()}. {last}"
        return (short_name, full_name, title)

    # 2. Фамилия впереди + инициалы: 'Чернов Д.В.', 'Чернов Д.'
    m_last = _LAST_FIRST_PATTERN.match(s)
    if m_last:
        last, i1, i2 = m_last.group(1), m_last.group(2), m_last.group(3)
        short_name = f"{i1.upper()}.{i2.upper()}. {last}" if i2 else f"{i1.upper()}. {last}"
        return (short_name, full_name, title)

    # 3. Полное ФИО: 'Чернов Денис Владимирович'
    parts = s.split()
    if len(parts) == 3 and all(p.replace("-", "").isalpha() for p in parts):
        last, first, patr = parts[0], parts[1], parts[2]
        short_name = f"{first[0].upper()}.{patr[0].upper()}. {last}"
        full_name = f"{last} {first} {patr}"
        return (short_name, full_name, title)

    if len(parts) == 2 and all(p.replace("-", "").isalpha() for p in parts):
        last, first = parts[0], parts[1]
        short_name = f"{first[0].upper()}. {last}"
        full_name = f"{last} {first}"
        return (short_name, full_name, title)

    return (short_name, full_name, title)
