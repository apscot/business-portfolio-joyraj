"""Financial-year helpers (pure). FY runs 1 Apr – 31 Mar and is labelled like ``2026-27``."""
import re
from datetime import date

_LABEL = re.compile(r"^(\d{4})-(\d{2})$")


def fy_label(start_year: int) -> str:
    """Label for the FY starting 1 Apr of ``start_year``."""
    return f"{start_year}-{(start_year + 1) % 100:02d}"


def fy_range(label: str) -> tuple[date, date]:
    """Return (first day, last day) inclusive of an FY label. Raises ValueError if invalid."""
    match = _LABEL.match(label)
    if match is None:
        raise ValueError(f"Invalid financial year label: {label!r}")
    start_year = int(match.group(1))
    if not 1 <= start_year < 9999 or int(match.group(2)) != (start_year + 1) % 100:
        raise ValueError(f"Invalid financial year label: {label!r}")
    return date(start_year, 4, 1), date(start_year + 1, 3, 31)


def fy_of(d: date) -> str:
    """FY label containing the given date."""
    return fy_label(d.year if d.month >= 4 else d.year - 1)


def current_fy(today: date | None = None) -> str:
    """FY label for ``today`` (defaults to the current date)."""
    return fy_of(today or date.today())


def list_fys(dates: list[date] | None = None, today: date | None = None) -> list[str]:
    """Distinct FY labels of ``dates`` plus the current FY, newest first."""
    labels = {fy_of(d) for d in dates or []}
    labels.add(current_fy(today))
    return sorted(labels, reverse=True)
