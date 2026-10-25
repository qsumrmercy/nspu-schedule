from datetime import datetime, timedelta, timezone as dt_timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from icalendar import Calendar, Event, Timezone, TimezoneStandard

from src.models import LessonEvent


def _create_vtimezone(timezone_name: str) -> Timezone:
    """Создает компонент VTIMEZONE для указанной таймзоны (по умолчанию Asia/Novosibirsk UTC+7)."""
    tz = Timezone()
    tz.add("tzid", timezone_name)
    std = TimezoneStandard()
    std.add("tzname", "+07")
    std.add("dtstart", datetime(1970, 1, 1, 0, 0, 0))
    std.add("tzoffsetfrom", timedelta(hours=7))
    std.add("tzoffsetto", timedelta(hours=7))
    tz.add_component(std)
    return tz


def build_icalendar(
    events: list[LessonEvent],
    calendar_name: str = "Расписание НГПУ (3.024.2.23)",
    timezone: str = "Asia/Novosibirsk",
) -> bytes:
    """Генерирует бинарные данные iCalendar (.ics) стандарта RFC 5545."""
    cal = Calendar()
    cal.add("prodid", "-//NSPU Schedule Generator//RU")
    cal.add("version", "2.0")
    cal.add("calscale", "GREGORIAN")
    cal.add("method", "PUBLISH")
    cal.add("x-wr-calname", calendar_name)
    cal.add("x-wr-timezone", timezone)

    cal.add_component(_create_vtimezone(timezone))

    tz_info = ZoneInfo(timezone)
    now_utc = datetime.now(dt_timezone.utc)

    for ev in events:
        event = Event()
        event.add("uid", ev.uid)
        event.add("dtstamp", now_utc)

        start_dt = ev.start_dt if ev.start_dt.tzinfo else ev.start_dt.replace(tzinfo=tz_info)
        end_dt = ev.end_dt if ev.end_dt.tzinfo else ev.end_dt.replace(tzinfo=tz_info)

        event.add("dtstart", start_dt)
        event.add("dtend", end_dt)
        event.add("summary", ev.summary)
        event.add("location", ev.location)
        event.add("description", ev.description)
        event.add("status", "CONFIRMED")
        event.add("transp", "OPAQUE")
        cal.add_component(event)

    return cal.to_ical()


def export_ics_files(ics_bytes: bytes, destinations: list[str]) -> None:
    """Сохраняет сгенерированный .ics файл во все указанные пути."""
    for dest in destinations:
        dest_path = Path(dest)
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        dest_path.write_bytes(ics_bytes)
