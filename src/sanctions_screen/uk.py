"""UK consolidated list (CSV, one row per name) -> Entity.

Layout follows the OFSI ConList.csv: a "Last Updated" line, then the header, then one
row per name, rows of the same Group ID belong to one entity.
"""

from __future__ import annotations

import csv
import re
from pathlib import Path

from .countries import to_iso2
from .model import Alias, Dob, Entity, IdDocument, make_id

SOURCE = "uk"

_GROUP_TYPES = {"Individual": "person", "Entity": "organization", "Ship": "vessel"}
_WEAK_ALIAS_TYPES = {"FKA"}


class ParseError(Exception):
    pass


def _parse_dob(raw: str) -> Dob | None:
    m = re.match(r"^(\d{2})/(\d{2})/(\d{4})$", raw.strip())
    if not m:
        return None
    day, month, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
    if day == 0 or month == 0:
        return Dob(kind="year", year=year)
    return Dob(kind="full", year=year, month=month, day=day)


def _row_name(row: dict[str, str], group_type: str) -> str:
    if group_type == "Individual":
        given = [row.get(f"Name {i}", "").strip() for i in range(1, 6)]
        parts = [p for p in given if p] + [row.get("Name 6", "").strip()]
        return " ".join(p for p in parts if p)
    return row.get("Name 6", "").strip()


def _list_date(raw: str) -> str | None:
    m = re.match(r"^(\d{2})/(\d{2})/(\d{4})$", raw.strip())
    return f"{m.group(3)}-{m.group(2)}-{m.group(1)}" if m else None


def parse_uk(path: str | Path) -> list[Entity]:
    try:
        text = Path(path).read_text(encoding="utf-8-sig", newline="")
    except OSError as exc:
        raise ParseError(f"cannot read UK list {path}: {exc}") from exc

    rows = list(csv.reader(text.splitlines()))
    list_date = None
    if rows and rows[0] and rows[0][0].strip() == "Last Updated":
        list_date = _list_date(rows[0][1]) if len(rows[0]) > 1 else None
        rows = rows[1:]
    if not rows:
        raise ParseError(f"{path}: empty file")
    header = rows[0]
    if "Group ID" not in header or "Name 6" not in header:
        raise ParseError(f"{path}: header does not look like the UK consolidated list")

    groups: dict[str, Entity] = {}
    for raw in rows[1:]:
        if not raw or len(raw) < len(header):
            continue
        row = dict(zip(header, raw, strict=False))
        gid = row["Group ID"].strip()
        gtype = row["Group Type"].strip()
        kind = _GROUP_TYPES.get(gtype)
        if not gid or kind is None:
            continue
        name = _row_name(row, gtype)
        if not name:
            continue
        alias_type = row.get("Alias Type", "").strip()
        ent = groups.get(gid)
        if ent is None:
            ent = Entity(
                id=make_id(SOURCE, gid), source=SOURCE, uid=gid, type=kind, name=name,
                list_date=list_date,
            )
            groups[gid] = ent
        elif name != ent.name and name not in {a.name for a in ent.aliases}:
            strength = "weak" if alias_type in _WEAK_ALIAS_TYPES else "strong"
            ent.aliases.append(Alias(name=name, strength=strength))

        dob = _parse_dob(row.get("DOB", ""))
        if dob and dob not in ent.dobs:
            ent.dobs.append(dob)
        nat = to_iso2(row.get("Nationality", ""))
        if nat and nat not in ent.nationalities:
            ent.nationalities.append(nat)
        passport = row.get("Passport Number", "").strip()
        if passport and not any(d.number == passport for d in ent.documents):
            ent.documents.append(IdDocument(kind="Passport", number=passport, country=nat))
        regime = row.get("Regime", "").strip()
        if regime and regime not in ent.programs:
            ent.programs.append(regime)
    return list(groups.values())
