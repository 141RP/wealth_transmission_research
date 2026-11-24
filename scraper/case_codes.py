"""Franklin County (Ohio) Probate Court case type and estate subtype codes.

Transcribed from the court's "General Case Search subtypes" PDF
(probate.franklincountyohio.gov, read Nov 24, 2026).
"""

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
