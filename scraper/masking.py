"""Masking so shared samples don't carry decedents' or fiduciaries' full names."""

from __future__ import annotations

import hashlib
import os
import re

_SUFFIXES = {"JR", "SR", "II", "III", "IV", "V"}
_SALT = os.environ.get("PROBATE_MASK_SALT", "change-me-locally")


def initials(name: str | None) -> str:
    """'DOE, JOHN B.' -> 'J.B.D.'; empty in, empty out."""
    if not name or not name.strip():
        return ""
    name = name.strip()
    if "," in name:
        last, rest = name.split(",", 1)
        parts = rest.split() + [last]
    else:
        parts = name.split()
    parts = [p for p in parts if p.strip(".,").upper() not in _SUFFIXES]
    letters = [p[0].upper() for p in parts if p and p[0].isalpha()]
    return ".".join(letters) + "." if letters else ""


def person_id(name: str | None) -> str:
    """Stable pseudonymous id, so the same person links across cases without the name."""
    if not name or not name.strip():
        return ""
    norm = re.sub(r"[^a-z]", "", name.lower())
    return hashlib.sha256((_SALT + norm).encode()).hexdigest()[:10]
