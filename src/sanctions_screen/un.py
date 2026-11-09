"""UN Security Council consolidated list (XML) -> Entity.

Parser antigo, mesmo estilo do ofac.py. Não mexer sem rodar os testes do índice.
"""
import re

from lxml import etree

from .countries import to_iso2
from .model import Alias, Dob, Entity, IdDocument, make_id

SOURCE = "un"


def _t(node, tag):
    el = node.find(tag)
    if el is None or el.text is None:
        return ""
    return el.text.strip()


def _values(node, path):
    return [e.text.strip() for e in node.findall(path) if e.text and e.text.strip()]


def _dob(node):
    kind = _t(node, "TYPE_OF_DATE")
    if kind == "BETWEEN":
        a, b = _t(node, "FROM_YEAR"), _t(node, "TO_YEAR")
        if a and b:
            return Dob(kind="range", year=int(a), year_to=int(b))
        return None
    date = _t(node, "DATE")
    if date:
        m = re.match(r"^(\d{4})-(\d{2})-(\d{2})", date)
        if m:
            k = "circa" if kind == "APPROXIMATE" else "full"
            return Dob(kind=k, year=int(m.group(1)), month=int(m.group(2)), day=int(m.group(3)))
    year = _t(node, "YEAR")
    if year:
        return Dob(kind="circa" if kind == "APPROXIMATE" else "year", year=int(year))
    return None


def _collect_aliases(node, tag):
    out = []
    for a in node.findall(tag):
        name = _t(a, "ALIAS_NAME")
        if not name:
            continue
        weak = _t(a, "QUALITY").lower() == "low"
        out.append(Alias(name=name, strength="weak" if weak else "strong"))
    # aliases fracos só valem quando são os únicos; senão é ruído (a.k.a. de baixa qualidade)
    if len(out) > 1:
        out = [a for a in out if a.strength == "strong"]
    return out


def _person_name(node):
    parts = [_t(node, t) for t in ("FIRST_NAME", "SECOND_NAME", "THIRD_NAME", "FOURTH_NAME")]
    return " ".join(p for p in parts if p)


def load_un(path):
    tree = etree.parse(str(path))
    root = tree.getroot()
    gen = root.get("dateGenerated") or ""
    list_date = gen[:10] if gen else None
    out = []
    n_ind = len(root.findall("INDIVIDUALS/INDIVIDUAL"))
    for node in root.findall("INDIVIDUALS/INDIVIDUAL"):
        ref = _t(node, "REFERENCE_NUMBER")
        if not ref:
            continue
        ent = Entity(
            id=make_id(SOURCE, ref), source=SOURCE, uid=ref, type="person",
            name=_person_name(node), list_date=list_date,
        )
        listed = _t(node, "UN_LIST_TYPE")
        if listed:
            ent.programs.append(listed)
        ent.aliases.extend(_collect_aliases(node, "INDIVIDUAL_ALIAS"))
        original = _t(node, "NAME_ORIGINAL_SCRIPT")
        if original:
            ent.aliases.append(Alias(name=original, strength="strong"))
        for d in node.findall("INDIVIDUAL_DATE_OF_BIRTH"):
            dob = _dob(d)
            if dob:
                ent.dobs.append(dob)
        for v in _values(node, "NATIONALITY/VALUE"):
            code = to_iso2(v)
            if code and code not in ent.nationalities:
                ent.nationalities.append(code)
        for d in node.findall("INDIVIDUAL_DOCUMENT"):
            number = _t(d, "NUMBER")
            if number:
                ent.documents.append(IdDocument(
                    kind=_t(d, "TYPE_OF_DOCUMENT"), number=number,
                    country=to_iso2(_t(d, "ISSUING_COUNTRY"))))
        out.append(ent)
    for node in root.findall("ENTITIES/ENTITY"):
        ref = _t(node, "REFERENCE_NUMBER")
        if not ref:
            continue
        ent = Entity(
            id=make_id(SOURCE, ref), source=SOURCE, uid=ref, type="organization",
            name=_t(node, "FIRST_NAME"), list_date=list_date,
        )
        listed = _t(node, "UN_LIST_TYPE")
        if listed:
            ent.programs.append(listed)
        ent.aliases.extend(_collect_aliases(node, "ENTITY_ALIAS"))
        original = _t(node, "NAME_ORIGINAL_SCRIPT")
        if original:
            ent.aliases.append(Alias(name=original, strength="strong"))
        out.append(ent)
    return out
