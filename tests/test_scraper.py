"""Tests on a made-up results table. Replace with saved real pages once inspected."""

from datetime import date, datetime

from scraper.client import in_backup_window
from scraper.config import COURT_TZ
from scraper.franklin import date_index_url, normalize, parse_tables
from scraper.masking import initials, person_id

FAKE_HTML = """
<table>
  <tr><th>Case Number</th><th>Case Name</th><th>Type</th><th>Subtype</th>
      <th>Open Date</th><th>Attorney</th></tr>
  <tr><td><a href="/netdata/case?id=1">600001</a></td><td>DOE, JANE Q.</td>
      <td>E</td><td>02</td><td>11/02/2026</td><td>SMITH, ALEX</td></tr>
  <tr><td>600002</td><td>ROE, RICHARD</td><td>E</td><td>19</td>
      <td>11/02/2026</td><td></td></tr>
</table>
"""


def test_date_index_url():
    assert date_index_url(date(2026, 11, 2)).endswith("string=20261102")


def test_parse_and_normalize():
    rows = parse_tables(FAKE_HTML)
    assert len(rows) == 2
    a, b = (normalize(r) for r in rows)
    assert a["case_number"] == "600001"
    assert a["case_type"] == "Estate"
    assert a["has_will"] is False and a["admin_tier"] == "full"
    assert a["has_attorney"] is True
    assert a["decedent_initials"] == "J.Q.D."
    assert "DOE" not in str(a.values())
    assert a["detail_url"].endswith("/netdata/case?id=1")
    assert b["has_will"] is True and b["admin_tier"] == "summary"
    assert b["has_attorney"] is False


def test_masking():
    assert initials("Doe, John B.") == "J.B.D."
    assert initials("") == ""
    assert person_id("Doe, John") == person_id("DOE,  JOHN")
    assert person_id("Doe, John") != person_id("Doe, Jane")


def test_backup_window():
    assert in_backup_window(datetime(2026, 11, 24, 23, 0, tzinfo=COURT_TZ))
    assert in_backup_window(datetime(2026, 11, 24, 1, 30, tzinfo=COURT_TZ))
    assert not in_backup_window(datetime(2026, 11, 24, 10, 0, tzinfo=COURT_TZ))
