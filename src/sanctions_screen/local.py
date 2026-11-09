"""data/lists/local_watchlist.csv -> Entity.

The local watchlist is curated by hand (internal adverse-media names and so on). It is
not downloaded from anywhere, so there is no way to rebuild it if the file is lost.
"""

from __future__ import annotations

import csv
from pathlib import Path

from .countries import to_iso2
from .model import Alias, Dob, Entity, make_id

SOURCE = "local"

_TYPES = {"person": "person", "organization": "organization", "vessel": "vessel"}


def _dob(raw: str) -> Dob | None:
    raw = raw.strip()
    if not raw:
        return None
    parts = raw.split("-")
    try:
        if len(parts) == 3:
            return Dob(kind="full", year=int(parts[0]), month=int(parts[1]), day=int(parts[2]))
        return Dob(kind="year", year=int(parts[0]))
    except ValueError:
        return None


def parse_local(path: str | Path) -> list[Entity]:
    out: list[Entity] = []
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            uid = (row.get("id") or "").strip()
            name = (row.get("name") or "").strip()
            kind = _TYPES.get((row.get("type") or "").strip())
            if not uid or not name or kind is None:
                continue
            ent = Entity(
                id=make_id(SOURCE, uid), source=SOURCE, uid=uid, type=kind, name=name,
                list_date=(row.get("added_on") or "").strip() or None,
            )
            for alias in (row.get("aliases") or "").split("|"):
                if alias.strip():
                    ent.aliases.append(Alias(name=alias.strip(), strength="strong"))
            dob = _dob(row.get("dob") or "")
            if dob:
                ent.dobs.append(dob)
            country = to_iso2(row.get("country"))
            if country:
                ent.nationalities.append(country)
            ent.programs.append("LOCAL")
            out.append(ent)
    return out
