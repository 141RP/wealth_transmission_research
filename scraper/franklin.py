"""Franklin County, Ohio probate: build search URLs and parse result pages.

The results pages haven't been inspected yet (the court's search was offline for
its nightly backup when this was written), so parsing is deliberately generic:
it reads any HTML table into header -> value rows and keeps every link. The
normalize step then maps whatever headers the court uses onto our research
fields. Once real pages are saved, tighten HEADER_ALIASES and add test fixtures.
"""

from __future__ import annotations

import re
from datetime import date
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from . import config
from .case_codes import ADMIN_TIER, CASE_TYPES, ESTATE_SUBTYPES
from .masking import initials, person_id


def date_index_url(day: date) -> str:
    return config.DATE_INDEX_URL.format(yyyymmdd=day.strftime("%Y%m%d"))


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def parse_tables(html: str, base_url: str = config.RESULTS_HOST) -> list[dict]:
    """Every data row of every table, as {header: text}, plus '_links' found in the row."""
    soup = BeautifulSoup(html, "html.parser")
    rows_out: list[dict] = []
    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        if len(rows) < 2:
            continue
        header_cells = rows[0].find_all(["th", "td"])
        headers = [_clean(c.get_text(" ")) or f"col{i}" for i, c in enumerate(header_cells)]
        for tr in rows[1:]:
            cells = tr.find_all(["td", "th"])
            if not cells:
                continue
            row = {headers[i] if i < len(headers) else f"col{i}": _clean(c.get_text(" "))
                   for i, c in enumerate(cells)}
            row["_links"] = [urljoin(base_url, a["href"]) for a in tr.find_all("a", href=True)]
            if any(v for k, v in row.items() if k != "_links"):
                rows_out.append(row)
    return rows_out


def parse_label_values(html: str) -> dict:
    """Case detail pages often list 'Label: value' pairs; collect them."""
    soup = BeautifulSoup(html, "html.parser")
    out: dict[str, str] = {}
    for tr in soup.find_all("tr"):
        cells = [_clean(c.get_text(" ")) for c in tr.find_all(["td", "th"])]
        for i in range(0, len(cells) - 1, 2):
            label = cells[i].rstrip(":")
            if label and len(label) < 60 and label not in out:
                out[label] = cells[i + 1]
    for line in soup.get_text("\n").splitlines():
        if ":" in line:
            label, value = line.split(":", 1)
            label, value = _clean(label), _clean(value)
            if label and value and len(label) < 60 and label not in out:
                out[label] = value
    return out


# Map our research fields to the header wording the court might use (lower-case).
HEADER_ALIASES = {
    "case_number": ["case number", "case no", "case #", "case", "number"],
    "case_name": ["case name", "name", "decedent", "estate of"],
    "open_date": ["open date", "date opened", "filed", "filing date", "case open date"],
    "case_type": ["type", "case type"],
    "subtype": ["subtype", "sub type", "case subtype"],
    "status": ["status", "case status"],
    "closed_date": ["closed", "close date", "date closed", "closed date"],
    "attorney": ["attorney", "attorney name", "counsel"],
    "fiduciary": ["fiduciary", "fiduciary name", "executor", "administrator"],
    "date_of_death": ["date of death", "dod", "death date"],
    "estate_value": ["value", "estate value", "total value", "gross estate", "inventory"],
}


def _pick(row: dict, field: str) -> str:
    lowered = {k.lower().rstrip(":"): v for k, v in row.items() if isinstance(v, str)}
    for alias in HEADER_ALIASES[field]:
        if alias in lowered and lowered[alias]:
            return lowered[alias]
    return ""


def _money(text: str) -> float | None:
    m = re.search(r"\$?\s*([\d,]+(?:\.\d{2})?)", text or "")
    return float(m.group(1).replace(",", "")) if m else None


def normalize(raw: dict) -> dict:
    """Turn a parsed row (or detail page) into one research record with names masked."""
    case_type = _pick(raw, "case_type")
    subtype = _pick(raw, "subtype")
    # Codes can arrive as 'E', 'E01' or 'E-01'; split them if needed.
    m = re.match(r"^\s*([A-Z]{1,2})[\s\-/]*(\d{2})\b", (case_type + " " + subtype).strip())
    if m and not subtype:
        case_type, subtype = m.group(1), m.group(2)
    sub_code = re.sub(r"\D", "", subtype)[:2]
    sub_desc, has_will = ESTATE_SUBTYPES.get(sub_code, ("", None))
    name = _pick(raw, "case_name")
    attorney = _pick(raw, "attorney")
    fiduciary = _pick(raw, "fiduciary")
    return {
        "county": "Franklin, OH",
        "case_number": _pick(raw, "case_number"),
        "open_date": _pick(raw, "open_date"),
        "closed_date": _pick(raw, "closed_date"),
        "status": _pick(raw, "status"),
        "case_type": CASE_TYPES.get(case_type.strip().upper(), case_type),
        "subtype_code": sub_code,
        "subtype": sub_desc or subtype,
        "has_will": has_will,
        "admin_tier": ADMIN_TIER.get(sub_code, ""),
        "decedent_initials": initials(name),
        "decedent_id": person_id(name),
        "fiduciary_id": person_id(fiduciary),
        "has_attorney": bool(attorney),
        "date_of_death": _pick(raw, "date_of_death"),
        "estate_value": _money(_pick(raw, "estate_value")),
        "detail_url": (raw.get("_links") or [""])[0],
    }
