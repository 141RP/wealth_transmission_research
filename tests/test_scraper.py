"""Tests against synthetic pages that copy the structure of the court's real ones.

The fixtures in tests/fixtures/ use made-up names and case numbers. Real court
pages stay in data/raw/, which git ignores.
"""

from datetime import date, datetime
from pathlib import Path

from scraper.case_codes import subtype_code_from_text
from scraper.client import in_backup_window
from scraper.config import COURT_TZ
from scraper.franklin import (FIELDS, build_record, case_urls, date_index_url, parse_docket,
                              parse_estate_detail, parse_fiduciaries, parse_index)
from scraper.masking import initials, person_id

FIX = Path(__file__).parent / "fixtures"


def page(name: str) -> str:
    return (FIX / name).read_text(encoding="utf-8")


def test_urls():
    assert date_index_url(date(2026, 11, 2)).endswith("PBODateInx.ndm/input?string=20261102")
    urls = case_urls("900002")
    assert urls["docket"].endswith("PBDocket.ndm/input?caseno=900002;;")
    assert urls["fiduciaries"].endswith("PBFidy.ndm/input?caseno=900002;;")


def test_parse_index_skips_nav_rows_and_finds_next_page():
    rows, next_url = parse_index(page("index_page.html"))
    assert [r["case_number"] for r in rows] == ["900001", "900002", "900003", "900004", "900005", "900006"]
    assert rows[0]["case_type"] == "ESTATE"
    assert rows[0]["closed"] == "03/06/2025"
    assert rows[1]["closed"] == ""
    assert rows[1]["detail_url"].endswith("ESTATE_DETAIL?caseno=900002;;")
    assert next_url.endswith("/netdata/PBODateInx.ndm/input?stringf=20250304900006")


def test_subtype_wording_maps_to_codes():
    assert subtype_code_from_text("RELEASE FROM ADMIN WITHOUT WILL") == "04"
    assert subtype_code_from_text("SUMMARY ADMINISTRATION W/WILL FRO") == "21"
    assert subtype_code_from_text("SUMMARY ADMINISTRATION W/O WILL") == "20"
    assert subtype_code_from_text("FULL ADMINISTRATION W/ALLEGED WILL") == "18"
    assert subtype_code_from_text("02 FULL ADMINISTRATION WITHOUT WILL") == "02"
    assert subtype_code_from_text("NAME CHANGE") == ""


def test_index_only_record():
    rows, _ = parse_index(page("index_page.html"))
    rec = build_record(rows[0])
    assert rec["subtype_code"] == "04" and rec["has_will"] is False
    assert rec["admin_tier"] == "release"
    assert rec["open_date"] == "2025-03-03" and rec["days_to_close"] == 3
    assert rec["is_open"] is False
    assert rec["decedent_initials"] == "A.B.T."
    assert rec["has_attorney"] is None  # unknown without the fiduciaries page


def test_full_record_from_all_pages():
    rows, _ = parse_index(page("index_page.html"))
    detail = parse_estate_detail(page("estate_detail.html"))
    fids = parse_fiduciaries(page("fiduciaries.html"))
    docket = parse_docket(page("docket.html"))

    assert "street" not in " ".join(detail).lower()
    assert detail["related_cases"] == 1
    assert fids[0]["title"] == "EXECUTOR" and fids[0]["attorney"]
    assert docket["subtype_code"] == "01" and docket["inventory_value"] == 210500.0
    assert docket["estate_tax_anticipated"] == "n"

    rec = build_record(rows[1], detail, fids, docket)
    assert set(rec) == set(FIELDS)
    assert rec["has_will"] is True and rec["admin_tier"] == "full"
    assert rec["date_of_death"] == "2025-01-15" and rec["days_death_to_open"] == 47
    assert rec["decedent_zip"] == "43215"
    assert rec["bond_amount"] == 125000.0
    assert rec["is_open"] is True and rec["days_to_close"] is None
    assert rec["fiduciary_title"] == "EXECUTOR"
    assert rec["fiduciary_same_surname"] is True
    assert rec["has_attorney"] is True
    assert rec["decedent_initials"] == "C.D.S."


def test_no_names_or_street_leak_into_records():
    rows, _ = parse_index(page("index_page.html"))
    rec = build_record(rows[1], parse_estate_detail(page("estate_detail.html")),
                       parse_fiduciaries(page("fiduciaries.html")), parse_docket(page("docket.html")))
    blob = " ".join(str(v) for v in rec.values()).upper()
    for secret in ("SAMPLE", "ERIN", "LAWYER", "NOWHERE", "123 "):
        assert secret not in blob


def test_masking():
    assert initials("Doe, John B.") == "J.B.D."
    assert initials("DOE, JOHN, JR.") == "J.D."
    assert initials("") == ""
    assert person_id("Doe, John") == person_id("DOE,  JOHN")
    assert person_id("Doe, John") != person_id("Doe, Jane")


def test_backup_window():
    assert in_backup_window(datetime(2026, 11, 24, 23, 0, tzinfo=COURT_TZ))
    assert in_backup_window(datetime(2026, 11, 24, 1, 30, tzinfo=COURT_TZ))
    assert not in_backup_window(datetime(2026, 11, 24, 10, 0, tzinfo=COURT_TZ))


def test_collect_skips_case_repeated_across_index_pages():
    """The court's next page begins with the last case of the page before it."""
    from scraper.run_sample import collect

    first = page("index_page.html")
    # Second page: repeats case 900005 (an estate) at the top, then one new estate.
    second = first.replace("900001", "900005", 1)
    for old, new in (("900002", "900007"), ("900003", "900008")):
        second = second.replace(old, new)

    class FakeClient:
        requests_made = 0

        def get(self, url):
            self.requests_made += 1
            if "stringf=20250304900006" in url:
                return second.replace("stringf=20250304900006", "stringf=end")
            if "stringf=end" in url:
                return "<html></html>"
            return first

    records = collect(FakeClient(), date(2025, 3, 3), 2, 50, details=False, all_types=False)
    numbers = [r["case_number"] for r in records]
    assert len(numbers) == len(set(numbers))
    assert numbers.count("900005") == 1
