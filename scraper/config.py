"""Settings for the Franklin County, Ohio probate demo scraper."""

from zoneinfo import ZoneInfo

# Public General Case Search of the Franklin County Probate Court (Columbus, OH).
SEARCH_PAGE = "https://probate.franklincountyohio.gov/Record-Search/General-Case-Search"
RESULTS_HOST = "https://probatesearch.franklincountyohio.gov"

# Search by case open date. The court's own form sends the date as YYYYMMDD.
DATE_INDEX_URL = RESULTS_HOST + "/netdata/PBODateInx.ndm/input?string={yyyymmdd}"

# Politeness: one request at a time, at least this many seconds apart.
MIN_SECONDS_BETWEEN_REQUESTS = 3.0
REQUEST_TIMEOUT_SECONDS = 30
MAX_RETRIES = 3

# Identify the client honestly. Put a contact address in PROBATE_SCRAPER_CONTACT
# (environment variable) before a real run.
USER_AGENT = "wealth-transmission-research demo scraper (academic, low volume{contact})"

# The court backs up its files each weekday evening between 10 PM and 2 AM
# Eastern; the search is unavailable then, so the scraper refuses to run.
COURT_TZ = ZoneInfo("America/New_York")
BACKUP_START_HOUR = 22
BACKUP_END_HOUR = 2

# Hard ceiling for the demo so a typo can't turn into a large crawl.
DEMO_MAX_CASES = 50
