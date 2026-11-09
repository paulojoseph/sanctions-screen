"""OFAC SDN.XML (classic format) -> Entity.

Escrito no começo do projeto, antes do modelo ficar estável. Mantido como está.
"""
import os
import re

from lxml import etree

from .countries import to_iso2
from .model import Alias, Dob, Entity, IdDocument, make_id

SOURCE = "ofac"

_TYPES = {
    "Individual": "person",
    "Entity": "organization",
    "Vessel": "vessel",
    "Aircraft": "aircraft",
}
_MONTHS = {m: i + 1 for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"])}


def _txt(node, tag):
    el = node.find("{*}" + tag)
    if el is None or el.text is None:
        return ""
    return el.text.strip()


def parse_dob_text(text):
    """'12 Mar 1971' | 'Mar 1971' | '1971' | 'circa 1971' | '1970 to 1972'"""
    t = text.strip().lower()
    if not t:
        return None
    circa = t.startswith("circa")
    if circa:
        t = t[5:].strip()
    m = re.match(r"^(\d{4}) to (\d{4})$", t)
    if m:
        return Dob(kind="range", year=int(m.group(1)), year_to=int(m.group(2)))
    m = re.match(r"^(\d{1,2}) ([a-z]{3}) (\d{4})$", t)
    if m and m.group(2) in _MONTHS:
        kind = "circa" if circa else "full"
        return Dob(kind=kind, year=int(m.group(3)), month=_MONTHS[m.group(2)], day=int(m.group(1)))
    m = re.match(r"^([a-z]{3}) (\d{4})$", t)
    if m:
        return Dob(kind="circa" if circa else "year", year=int(m.group(2)))
    m = re.match(r"^(\d{4})$", t)
    if m:
        return Dob(kind="circa" if circa else "year", year=int(m.group(1)))
    return None


def _full_name(node):
    first = _txt(node, "firstName")
    last = _txt(node, "lastName")
    return (first + " " + last).strip()


def _publish_date(root):
    info = root.find("{*}publshInformation")  # sic, the typo is in the official file
    if info is None:
        return None
    raw = _txt(info, "Publish_Date")
    m = re.match(r"^(\d{2})/(\d{2})/(\d{4})$", raw)
    if not m:
        return None
    return f"{m.group(3)}-{m.group(1)}-{m.group(2)}"


def load_sdn(path):
    tree = etree.parse(str(path))
    root = tree.getroot()
    list_date = _publish_date(root)
    out = []
    skipped = 0
    for entry in root.findall("{*}sdnEntry"):
        try:
            uid = _txt(entry, "uid")
            kind = _TYPES.get(_txt(entry, "sdnType"))
            if not uid or kind is None:
                skipped += 1
                continue
            ent = Entity(
                id=make_id(SOURCE, uid),
                source=SOURCE,
                uid=uid,
                type=kind,
                name=_full_name(entry),
                list_date=list_date,
            )
            for prog in entry.findall("{*}programList/{*}program"):
                if prog.text:
                    ent.programs.append(prog.text.strip())
            for aka in entry.findall("{*}akaList/{*}aka"):
                nm = _full_name(aka)
                if nm:
                    strength = "weak" if _txt(aka, "category") == "weak" else "strong"
                    ent.aliases.append(Alias(name=nm, strength=strength))
            for item in entry.findall("{*}dateOfBirthList/{*}dateOfBirthItem"):
                dob = parse_dob_text(_txt(item, "dateOfBirth"))
                if dob:
                    ent.dobs.append(dob)
            for nat in entry.findall("{*}nationalityList/{*}nationality"):
                code = to_iso2(_txt(nat, "country"))
                if code and code not in ent.nationalities:
                    ent.nationalities.append(code)
            for idn in entry.findall("{*}idList/{*}id"):
                number = _txt(idn, "idNumber")
                if number:
                    ent.documents.append(IdDocument(
                        kind=_txt(idn, "idType"), number=number, country=to_iso2(_txt(idn, "idCountry"))))
            out.append(ent)
        except Exception as exc:
            print("ofac: skipping entry:", exc)
            skipped += 1
    return out
