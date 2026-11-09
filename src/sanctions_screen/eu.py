"""EU financial sanctions file (FSF, XML export) -> Entity."""

from __future__ import annotations

from pathlib import Path

from lxml import etree

from .countries import to_iso2
from .model import Alias, Dob, Entity, IdDocument, make_id

SOURCE = "eu"


class ParseError(Exception):
    pass


def _int(value: str | None) -> int | None:
    try:
        return int(value) if value else None
    except ValueError:
        return None


def _parse_birthdate(node: etree._Element) -> Dob | None:
    year = _int(node.get("year"))
    if year is None:
        return None
    month = _int(node.get("monthOfYear"))
    day = _int(node.get("dayOfMonth"))
    circa = node.get("circa") == "true"
    if circa:
        return Dob(kind="circa", year=year, month=month, day=day)
    if month and day:
        return Dob(kind="full", year=year, month=month, day=day)
    return Dob(kind="year", year=year)


def _entity_from_node(node: etree._Element, list_date: str | None) -> Entity | None:
    uid = node.get("logicalId")
    if not uid:
        return None
    subject = node.find("{*}subjectType")
    code = subject.get("classificationCode") if subject is not None else None
    kind = {"person": "person", "enterprise": "organization"}.get(code or "")
    if kind is None:
        return None

    names = node.findall("{*}nameAlias")
    primary = next((n.get("wholeName") for n in names if n.get("wholeName")), None)
    if not primary:
        return None
    ent = Entity(
        id=make_id(SOURCE, uid), source=SOURCE, uid=uid, type=kind, name=primary,
        list_date=list_date,
    )
    seen = {primary}
    for n in names:
        whole = n.get("wholeName")
        if not whole or whole in seen:
            continue
        seen.add(whole)
        strong = n.get("strong", "true") == "true"
        ent.aliases.append(Alias(name=whole, strength="strong" if strong else "weak"))

    for reg in node.findall("{*}regulation"):
        prog = reg.get("programme")
        if prog and prog not in ent.programs:
            ent.programs.append(prog)
    for b in node.findall("{*}birthdate"):
        dob = _parse_birthdate(b)
        if dob:
            ent.dobs.append(dob)
    for c in node.findall("{*}citizenship"):
        iso = to_iso2(c.get("countryIso2Code"))
        if iso and iso not in ent.nationalities:
            ent.nationalities.append(iso)
    for ident in node.findall("{*}identification"):
        number = ident.get("number")
        if number:
            ent.documents.append(IdDocument(
                kind=ident.get("identificationTypeCode") or "id",
                number=number,
                country=to_iso2(ident.get("countryIso2Code")),
            ))
    return ent


def parse_eu(path: str | Path) -> list[Entity]:
    try:
        root = etree.parse(str(path)).getroot()
    except (OSError, etree.XMLSyntaxError) as exc:
        raise ParseError(f"cannot read EU list {path}: {exc}") from exc
    if not root.tag.endswith("export"):
        raise ParseError(f"{path}: root element is {root.tag!r}, expected 'export'")
    generated = root.get("generationDate") or ""
    list_date = generated[:10] or None
    out = []
    for node in root.findall("{*}sanctionEntity"):
        ent = _entity_from_node(node, list_date)
        if ent is not None:
            out.append(ent)
    return out
