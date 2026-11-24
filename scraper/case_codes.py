"""Franklin County (Ohio) Probate Court case type and estate subtype codes.

Transcribed from the court's "General Case Search subtypes" PDF
(probate.franklincountyohio.gov, read Nov 24, 2026).
"""

import re

CASE_TYPES = {
    "C": "Civil Action",
    "E": "Estate",
    "GA": "Guardianship Adult",
    "GM": "Guardianship Minor",
    "M": "Miscellaneous",
    "T": "Trust",
}

# Estate subtypes, with a research-friendly flag for whether a will is involved.
# will: True = testate, False = intestate, None = not applicable / unclear.
ESTATE_SUBTYPES = {
    "01": ("Full Administration with Will", True),
    "02": ("Full Administration without Will", False),
    "03": ("Release from Admin with Will", True),
    "04": ("Release from Admin without Will", False),
    "05": ("Wrongful Death Only", None),
    "06": ("Wrongful Death with Probate Assets", None),
    "07": ("Probate Only w/ or w/o Real Estate", None),
    "08": ("Tax Only", None),
    "09": ("Will Filed for Record Only", True),
    "10": ("Will Filed for Record Only & Tax", True),
    "11": ("Real Estate Only w/o Will", False),
    "12": ("Real Estate Transfer & Tax", None),
    "13": ("Foreign Record", None),
    "14": ("Right of Action", None),
    "15": ("Miscellaneous - Estate", None),
    "16": ("Ancillary Administration", None),
    "17": ("Release from Admin Will FRO", True),
    "18": ("Full Administration w/ Alleged Will", True),
    "19": ("Summary Administration w/ Will", True),
    "20": ("Summary Administration w/o Will", False),
    "21": ("Summary Administration w/ Will FRO", True),
    "22": ("Inventory Safe Deposit Box", None),
    "23": ("Disclaimer", None),
    "24": ("Wrongful Death Only with Will", True),
    "25": ("Wrongful Death w/ Will - Probate Assets", True),
    "26": ("Right of Action with Will", True),
    "27": ("Release Decedent's Medical Records", None),
    "28": ("Beneficiary Placeholder", None),
}

# Rough administration tier, useful as a proxy for estate size in Ohio:
# release from administration and summary release apply to smaller estates.
ADMIN_TIER = {
    "01": "full", "02": "full", "18": "full",
    "03": "release", "04": "release", "17": "release",
    "19": "summary", "20": "summary", "21": "summary",
}


def _norm_subtype(text: str) -> str:
    """Make the court's spellings comparable: 'W/O WILL', 'without Will', 'ADMINISTRATION' vs 'ADMIN'."""
    t = (text or "").upper()
    t = t.replace("W/O", " WITHOUT ").replace("W/", " WITH ")
    t = re.sub(r"[^A-Z0-9 ]", " ", t)
    t = re.sub(r"\bADMINISTRATION\b", "ADMIN", t)
    return re.sub(r"\s+", " ", t).strip()


_SUBTYPE_BY_TEXT = {_norm_subtype(desc): code for code, (desc, _) in ESTATE_SUBTYPES.items()}


def subtype_code_from_text(text: str) -> str:
    """Map the subtype wording shown on the index and detail pages to its two-digit code.

    Accepts a leading code ('02 FULL ADMINISTRATION WITHOUT WILL'), exact wording in
    any of the court's spellings, or a label cut short by the index page's column width.
    Returns '' when nothing matches.
    """
    m = re.match(r"\s*(\d{2})\b", text or "")
    if m and m.group(1) in ESTATE_SUBTYPES:
        return m.group(1)
    key = _norm_subtype(text)
    if not key:
        return ""
    if key in _SUBTYPE_BY_TEXT:
        return _SUBTYPE_BY_TEXT[key]
    prefixed = [code for norm, code in _SUBTYPE_BY_TEXT.items() if norm.startswith(key) or key.startswith(norm)]
    # Prefer the longest matching description so 'WITH WILL FRO' beats 'WITH WILL'.
    prefixed.sort(key=lambda c: -len(_norm_subtype(ESTATE_SUBTYPES[c][0])))
    return prefixed[0] if prefixed else ""
