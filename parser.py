import json
import os
from datetime import datetime, timezone
from pathlib import Path
import urllib.error
import urllib.request

from src.ics_builder import build_icalendar, export_ics_files
from src.models import get_default_config
from src.session_parser import parse_schedule_html

URL = "https://schedule.nspu.ru/group_shedule_1s.php?n=3.024.2.23"
DAYS = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]


def fetch_html(url: str = URL, fallback_path: Path | None = None, timeout: int = 10) -> str:
    fb = fallback_path or Path("page.html")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception as exc:
        print(f"Network request failed ({exc}), falling back to {fb}")
        if fb.exists():
            return fb.read_text(encoding="utf-8")
        raise RuntimeError(f"Failed to fetch schedule and {fb} not found") from exc


def main(output_dir: Path = Path("."), downloads_dir: Path | None = None) -> list:
    dl_dir = downloads_dir or Path(os.environ.get("DOWNLOADS_DIR", r"C:\Users\User\Downloads"))
    fb = output_dir / "page.html" if (output_dir / "page.html").exists() else Path("page.html")
    html = fetch_html(fallback_path=fb)
    events = parse_schedule_html(html)

    ics_bytes = build_icalendar(events)
    ics_paths = [str(output_dir / "schedule-nspu.ics"), str(dl_dir / "schedule-nspu.ics")]
    saved_ics = []
    for p in ics_paths:
        try:
            export_ics_files(ics_bytes, [p])
            saved_ics.append(p)
        except (PermissionError, OSError) as exc:
            print(f"Предупреждение: Не удалось сохранить в {p}: {exc}")

    cfg = get_default_config()
    widget = {
        "group": "3.024.2.23",
        "faculty": "ИОДО НГПУ",
        "direction": "44.03.01 Педагогическое образование, Дополнительное образование",
        "timezone": cfg.timezone,
        "semester_dates": {
            "start": cfg.start_date.isoformat(),
            "end": cfg.end_date.isoformat(),
            "session_start": cfg.session_start.isoformat(),
            "session_end": cfg.session_end.isoformat(),
        },
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "events": [
            {
                "summary": e.summary,
                "location": e.location,
                "teacher": e.description.splitlines()[-1].replace("Преподаватель: ", "") if e.description else "",
                "time": f"{e.start_dt.strftime('%H:%M')} - {e.end_dt.strftime('%H:%M')}",
                "date": e.start_dt.strftime("%Y-%m-%d"),
                "day_of_week": DAYS[e.start_dt.weekday()],
                "week_number": ((e.start_dt.date() - cfg.week1_monday).days // 7) + 1,
                "is_session": e.is_session,
                "type": e.lesson_type,
                "uid": e.uid,
            }
            for e in events
        ],
    }

    json_path = output_dir / "events.json"
    json_path.write_text(json.dumps(widget, ensure_ascii=False, indent=2), encoding="utf-8")

    reg_cnt = sum(1 for e in events if not e.is_session)
    ses_cnt = sum(1 for e in events if e.is_session)
    print("=== Отчет генерации расписания ===")
    print(f"Всего событий: {len(events)} (регулярных: {reg_cnt}, сессионных: {ses_cnt})")
    print(f"ICS сохранен: {', '.join(saved_ics)}")
    print(f"JSON сохранен: {json_path}")
    return events


if __name__ == "__main__":
    main()
