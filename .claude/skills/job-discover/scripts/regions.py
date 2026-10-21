"""
regions.py — region of a posting from its location, used to group the report.

Per country: department (or province) codes → region, plus region names matched in free-text locations
("Nice, Provence-Alpes-Côte d'Azur, France"). Add a country by adding an entry to REGIONS.
"""
from __future__ import annotations

import re
import unicodedata

REMOTE = "Remote"
UNKNOWN = "Unknown"

REGIONS: dict[str, dict[str, list[str]]] = {
    "FR": {
        "Auvergne-Rhône-Alpes": ["01", "03", "07", "15", "26", "38", "42", "43", "63", "69", "73", "74"],
        "Bourgogne-Franche-Comté": ["21", "25", "39", "58", "70", "71", "89", "90"],
        "Bretagne": ["22", "29", "35", "56"],
        "Centre-Val de Loire": ["18", "28", "36", "37", "41", "45"],
        "Corse": ["2A", "2B", "20"],
        "Grand Est": ["08", "10", "51", "52", "54", "55", "57", "67", "68", "88"],
        "Hauts-de-France": ["02", "59", "60", "62", "80"],
        "Île-de-France": ["75", "77", "78", "91", "92", "93", "94", "95", "Paris"],
        "Normandie": ["14", "27", "50", "61", "76"],
        "Nouvelle-Aquitaine": ["16", "17", "19", "23", "24", "33", "40", "47", "64", "79", "86", "87"],
        "Occitanie": ["09", "11", "12", "30", "31", "32", "34", "46", "48", "65", "66", "81", "82"],
        "Pays de la Loire": ["44", "49", "53", "72", "85"],
        "Provence-Alpes-Côte d'Azur": ["04", "05", "06", "13", "83", "84"],
        "Outre-mer": ["971", "972", "973", "974", "976"],
    },
}
CODE_RE = re.compile(r"^\s*(\d{2,3}|2[ab])\b", re.IGNORECASE)  # "78 - Magny-les-Hameaux"


def _plain(text: str) -> str:
    return unicodedata.normalize("NFKD", text.lower()).encode("ascii", "ignore").decode()


def region_of(location: str, remote: str = "", country: str = "") -> str:
    """Region name, REMOTE for a fully remote posting without a place, or UNKNOWN."""
    table = REGIONS.get(country.upper(), {}) if country else {k: v for t in REGIONS.values() for k, v in t.items()}
    m = CODE_RE.match(location or "")
    if m:
        code = m.group(1).upper()
        for region, codes in table.items():
            if code in codes:
                return region
    plain = _plain(location or "")
    for region, codes in table.items():
        names = [region] + [c for c in codes if not c[0].isdigit()]
        if any(re.search(rf"\b{re.escape(_plain(n))}\b", plain) for n in names):
            return region
    if remote == "full" and not plain.strip(" ,france"):
        return REMOTE
    return UNKNOWN
