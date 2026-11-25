"""Franklin County, Ohio probate: build search URLs and parse the court's pages.

Written against the live pages as they looked on Nov 24, 2026. Four page kinds
matter for the demo:

* the open-date index (``PBODateInx.ndm``): 40 cases per page, all case types
  mixed together, with "Next Cases >>" paging;
* the estate detail page (``ESTATE_DETAIL``): label/value rows such as date of
  death, bond amount and the decedent's zip;
* the fiduciaries page (``PBFidy.ndm``): who was appointed, their title, and
  their attorney;
* the docket (``PBDocket.ndm``): numbered filings, including the inventory
  value when one has been filed.

The court nests tables inside tables, so every parser below reads only the
innermost rows. Names are used in memory to compute masked fields and are never
returned by ``build_record``. The decedent's street address is never read.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

from . import config
from .case_codes import ADMIN_TIER, ESTATE_SUBTYPES, subtype_code_from_text
from .masking import initials, person_id

INDEX_BASE = config.RESULTS_HOST + "/netdata/PBODateInx.ndm/"


def date_index_url(day: date) -> str:
    return config.DATE_INDEX_URL.format(yyyymmdd=day.strftime("%Y%m%d"))


def case_urls(case_number: str) -> dict[str, str]:
    """Detail, fiduciary and docket pages for an estate case."""
    host = config.RESULTS_HOST + "/netdata"
    key = f"{case_number};;"
    return {
        "detail": f"{host}/PBCaseTypeE.ndm/ESTATE_DETAIL?caseno={key}",
        "fiduciaries": f"{host}/PBFidy.ndm/input?caseno={key}",
        "docket": f"{host}/PBDocket.ndm/input?caseno={key}",
    }


# --------------------------------------------------------------------- helpers

def _clean(text: str | None) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _leaf_rows(soup: BeautifulSoup | Tag) -> list[Tag]:
    """<tr> elements that don't wrap another table (the court nests tables)."""
    return [tr for tr in soup.find_all("tr") if tr.find("table") is None]


def _cells(tr: Tag) -> list[Tag]:
    return tr.find_all(["th", "td"], recursive=False)


def _date(text: str) -> date | None:
    text = _clean(text)
    for fmt in ("%m/%d/%Y", "%m/%d/%y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            pass
    return None


def _money(text: str) -> float | None:
    m = re.search(r"([\d,]*\d(?:\.\d+)?|\.\d+)", text or "")
    return float(m.group(1).replace(",", "")) if m else None


def _surname(name: str) -> str:
    """'DOE, JANE Q.' -> 'DOE'. Used only in memory, never written out."""
    name = _clean(name).upper()
    return re.sub(r"[^A-Z]", "", name.split(",")[0]) if name else ""


def _header_table(html: str, first_header: str) -> tuple[list[str], list[Tag]]:
    """Find the row of <th> cells that starts with ``first_header`` and the data rows after it."""
    soup = BeautifulSoup(html, "html.parser")
    for tr in _leaf_rows(soup):
        heads = [_clean(c.get_text(" ")) for c in tr.find_all("th", recursive=False)]
        if heads and heads[0].lower() == first_header.lower():
            rows = [r for r in tr.find_next_siblings("tr") if r.find("table") is None]
            return heads, rows
    return [], []


# ----------------------------------------------------------------- index pages

INDEX_COLUMNS = {
    "case number": "case_number", "case name": "case_name", "type": "case_type",
    "subtype": "subtype_text", "status": "status", "opened": "opened", "closed": "closed",
}


def parse_index(html: str, base_url: str = INDEX_BASE) -> tuple[list[dict], str | None]:
    """Rows of an open-date index page, and the absolute URL of the next page (or None)."""
    heads, rows = _header_table(html, "Case Number")
    keys = [INDEX_COLUMNS.get(h.lower(), h) for h in heads]
    out: list[dict] = []
    for tr in rows:
        cells = _cells(tr)
        if len(cells) != len(keys):
            continue  # paging / navigation rows
        row = {k: _clean(c.get_text(" ")) for k, c in zip(keys, cells)}
        if not re.fullmatch(r"\d+", row.get("case_number", "")):
            continue
        link = cells[0].find("a", href=True)
        row["detail_url"] = urljoin(base_url, link["href"]) if link else ""
        out.append(row)

    soup = BeautifulSoup(html, "html.parser")
    nxt = soup.find("a", string=re.compile(r"Next Cases", re.I), href=True)
    return out, (urljoin(base_url, nxt["href"]) if nxt else None)


# ---------------------------------------------------------------- case pages

DETAIL_FIELDS = {
    "case name": "case_name", "case subtype": "subtype_text", "zip": "zip",
    "date of death": "date_of_death", "bond amount": "bond_amount",
    "date opened": "opened", "date closed": "closed",
}


def parse_estate_detail(html: str) -> dict:
    """Label/value rows of an estate detail page. Street address is skipped on purpose."""
    out: dict = {}
    related = 0
    for tr in _leaf_rows(BeautifulSoup(html, "html.parser")):
        cells = _cells(tr)
        if len(cells) != 2:
            continue
        label = _clean(cells[0].get_text(" ")).rstrip(":").lower()
        value = _clean(cells[1].get_text(" "))
        if label.startswith("related case") and value:
            related += 1
        elif label in DETAIL_FIELDS:
            out[DETAIL_FIELDS[label]] = value
    out["related_cases"] = related
    return out


def parse_fiduciaries(html: str) -> list[dict]:
    """One dict per fiduciary: name (in memory only), title, appointment date, attorney."""
    heads, rows = _header_table(html, "Fiduciary No.")
    keys = [h.lower() for h in heads]
    out = []
    for tr in rows:
        cells = _cells(tr)
        if len(cells) != len(keys):
            continue
        row = dict(zip(keys, (_clean(c.get_text(" ")) for c in cells)))
        attorney = row.get("attorney name", "")
        out.append({
            "name": row.get("estate fiduciaries", ""),
            "title": row.get("title description", ""),
            "appointed": row.get("appt date", ""),
            "attorney": "" if attorney in ("", "N/A") else attorney,
        })
    return out


def parse_docket(html: str) -> dict:
    """Subtype code from the docket header, plus a few facts from coded filings.

    Only rows that carry a date and a filing code are read. The continuation rows
    under them hold people's names and addresses and are ignored.
    """
    soup = BeautifulSoup(html, "html.parser")
    out: dict = {"subtype_code": "", "inventory_value": None, "filings": 0,
                 "estate_tax_anticipated": ""}
    for tr in _leaf_rows(soup):
        cells = [_clean(c.get_text(" ")) for c in _cells(tr)]
        if len(cells) == 2 and cells[0].rstrip(":").lower() == "case subtype":
            m = re.match(r"(\d{2})\b", cells[1])
            out["subtype_code"] = m.group(1) if m else subtype_code_from_text(cells[1])
        elif len(cells) == 6 and _date(cells[0]) and cells[1]:
            out["filings"] += 1
            code, desc, ref = cells[1].lower(), cells[2].lower(), cells[3]
            if code == "6.0" and desc.startswith("inventory"):
                out["inventory_value"] = _money(ref)
            elif desc.startswith("ohio estate tax anticipated"):
                out["estate_tax_anticipated"] = ref.lower()[:1]
    return out


# ------------------------------------------------------------------- records

FIELDS = [
    "county", "case_number", "case_type", "subtype_code", "subtype", "has_will",
    "admin_tier", "status", "open_date", "closed_date", "is_open", "days_to_close",
    "decedent_initials", "decedent_id", "date_of_death", "days_death_to_open",
    "decedent_zip", "bond_amount", "inventory_value", "estate_tax_anticipated",
    "related_cases", "n_fiduciaries", "fiduciary_title", "fiduciary_id",
    "fiduciary_same_surname", "has_attorney",
]


def build_record(index_row: dict, detail: dict | None = None,
                 fiduciaries: list[dict] | None = None, docket: dict | None = None) -> dict:
    """Combine what we parsed for one case into a masked research record."""
    detail, docket, fiduciaries = detail or {}, docket or {}, fiduciaries or []
    subtype_text = detail.get("subtype_text") or index_row.get("subtype_text", "")
    code = docket.get("subtype_code") or subtype_code_from_text(subtype_text)
    desc, has_will = ESTATE_SUBTYPES.get(code, (subtype_text.title(), None))

    opened = _date(detail.get("opened") or index_row.get("opened", ""))
    closed = _date(detail.get("closed") or index_row.get("closed", ""))
    died = _date(detail.get("date_of_death", ""))
    name = detail.get("case_name") or index_row.get("case_name", "")
    first = fiduciaries[0] if fiduciaries else {}
    bond = detail.get("bond_amount", "")

    return {
        "county": "Franklin, OH",
        "case_number": index_row.get("case_number", ""),
        "case_type": index_row.get("case_type", "").title(),
        "subtype_code": code,
        "subtype": desc,
        "has_will": has_will,
        "admin_tier": ADMIN_TIER.get(code, "other"),
        "status": index_row.get("status", ""),
        "open_date": opened.isoformat() if opened else "",
        "closed_date": closed.isoformat() if closed else "",
        "is_open": closed is None,
        "days_to_close": (closed - opened).days if opened and closed else None,
        "decedent_initials": initials(name),
        "decedent_id": person_id(name),
        "date_of_death": died.isoformat() if died else "",
        "days_death_to_open": (opened - died).days if opened and died else None,
        "decedent_zip": detail.get("zip", "")[:5],
        "bond_amount": _money(bond) if bond and bond != "N/A" else None,
        "inventory_value": docket.get("inventory_value"),
        "estate_tax_anticipated": docket.get("estate_tax_anticipated", ""),
        "related_cases": detail.get("related_cases"),
        "n_fiduciaries": len(fiduciaries) if fiduciaries else None,
        "fiduciary_title": first.get("title", ""),
        "fiduciary_id": person_id(first.get("name", "")),
        "fiduciary_same_surname": (_surname(first["name"]) == _surname(name))
                                  if first.get("name") and name else None,
        "has_attorney": any(f.get("attorney") for f in fiduciaries) if fiduciaries else None,
    }
