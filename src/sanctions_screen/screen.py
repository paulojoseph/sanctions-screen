"""Screening pipeline: load lists, normalize, score, apply boosts, filter decisions, format.

This module grew feature by feature and it shows. Splitting it is on the roadmap.
"""

from __future__ import annotations

import csv
import io
import json
import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from rapidfuzz.distance import JaroWinkler

from . import config, eu, local, match, normalize, ofac, uk, un
from . import decisions as decisions_mod
from .countries import to_iso2
from .index import Index, build_index, load_index
from .model import Dob, Entity

# filled by get_index(); keyed by the path string the caller passed in
_INDEX_CACHE: dict[str, Index] = {}

_MONTHS = {m: i + 1 for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"])}

# (source, filename patterns, parser). First pattern that matches a file wins.
LIST_FILES = [
    ("ofac", ["ofac*.xml", "sdn*.xml"], ofac.load_sdn),
    ("un", ["un_*.xml", "un*.xml"], un.load_un),
    ("eu", ["eu_*.xml", "fsf*.xml"], eu.parse_eu),
    ("uk", ["uk_*.csv", "conlist*.csv"], uk.parse_uk),
    ("local", ["local_watchlist.csv"], local.parse_local),
]


# ----------------------------------------------------------------------------------------
# loading
# ----------------------------------------------------------------------------------------

def find_list_file(directory: Path, patterns: list[str]) -> Path | None:
    for pattern in patterns:
        found = sorted(directory.glob(pattern))
        if found:
            return found[0]
    return None


def load_lists(directory: str | Path) -> list[Entity]:
    """Every list we know about that is present in `directory`, parsed and concatenated."""
    directory = Path(directory)
    if not directory.is_dir():
        raise FileNotFoundError(f"{directory} is not a directory")
    entities: list[Entity] = []
    for _source, patterns, parser in LIST_FILES:
        path = find_list_file(directory, patterns)
        if path is None:
            continue
        entities.extend(parser(path))
    return entities


def load_one(path: str | Path) -> list[Entity]:
    """Parse a single list file, the parser is picked from the file name."""
    path = Path(path)
    for _source, patterns, parser in LIST_FILES:
        if any(path.match(p) for p in patterns):
            return parser(path)
    raise ValueError(f"don't know which list {path.name} is (expected ofac*, un*, eu*, uk*)")


def get_index(path: str | Path) -> Index:
    """Index from a saved index file, or built on the fly from a directory of lists."""
    key = str(path)
    cached = _INDEX_CACHE.get(key)
    if cached is not None:
        return cached
    p = Path(path)
    if p.is_dir():
        idx = build_index(load_lists(p))
    elif p.exists():
        idx = load_index(p)
    else:
        raise FileNotFoundError(
            f"no index or lists directory at {p}. Run `sanctions-screen index` first."
        )
    _INDEX_CACHE[key] = idx
    return idx


# ----------------------------------------------------------------------------------------
# query side
# ----------------------------------------------------------------------------------------

@dataclass
class Query:
    name: str
    dob: str | None = None
    country: str | None = None
    customer_id: str | None = None

    @property
    def ref(self) -> str:
        return decisions_mod.customer_ref(self.customer_id, self.name)


def parse_query_dob(text: str | None) -> Dob | None:
    """Accepts 1971, 1971-03, 1971-03-12, 12/03/1971, 12 Mar 1971 and 'circa 1971'."""
    if not text:
        return None
    t = text.strip().lower()
    if not t:
        return None
    circa = t.startswith("circa") or t.startswith("c.") or t.startswith("~")
    t = re.sub(r"^(circa|c\.|~)\s*", "", t)
    m = re.match(r"^(\d{4})$", t)
    if m:
        return Dob(kind="circa" if circa else "year", year=int(m.group(1)))
    m = re.match(r"^(\d{4})-(\d{2})$", t)
    if m:
        return Dob(kind="circa" if circa else "year", year=int(m.group(1)))
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", t)
    if m:
        return _full(int(m.group(1)), int(m.group(2)), int(m.group(3)), circa)
    m = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})$", t)
    if m:
        return _full(int(m.group(3)), int(m.group(2)), int(m.group(1)), circa)
    m = re.match(r"^(\d{1,2}) ([a-z]{3}) (\d{4})$", t)
    if m and m.group(2) in _MONTHS:
        return _full(int(m.group(3)), _MONTHS[m.group(2)], int(m.group(1)), circa)
    return None


def _full(year: int, month: int, day: int, circa: bool) -> Dob | None:
    try:
        date(year, month, day)
    except ValueError:
        return None
    return Dob(kind="circa" if circa else "full", year=year, month=month, day=day)


def query_country(text: str | None) -> str | None:
    if not text:
        return None
    iso = to_iso2(text)
    if iso:
        return iso
    t = text.strip().upper()
    return t if len(t) == 2 and t.isalpha() else None


# ----------------------------------------------------------------------------------------
# boosts and penalties
# ----------------------------------------------------------------------------------------

def _to_date(dob: Dob) -> date | None:
    if dob.year is None:
        return None
    try:
        return date(dob.year, dob.month or 1, dob.day or 1)
    except ValueError:
        return None


def dob_adjust(query: Dob | None, ent: Entity) -> tuple[float, str]:
    """Score delta and a short note for the date of birth. 0.0 when there's nothing to compare."""
    if query is None or not ent.dobs:
        return 0.0, ""
    qd = _to_date(query)
    if qd is None:
        return 0.0, ""
    best: tuple[float, str] | None = None
    for d in ent.dobs:
        if d.kind == "range" and d.year_to:
            if d.year <= query.year <= d.year_to:
                cand = (0.03, f"dob {query.year} inside listed range {d.label()}")
            else:
                cand = (-0.10, f"dob {query.year} outside listed range {d.label()}")
        else:
            ed = _to_date(d)
            if ed is None:
                continue
            gap = abs((qd - ed).days)
            if gap == 0:
                cand = (0.06, f"dob matches {d.label()}")
            elif gap <= config.DOB_TYPO_DAYS:
                cand = (0.0, f"dob {gap} days from {d.label()}, treated as a typo")
            else:
                cand = (-0.10, f"dob does not match {d.label()}")
        if best is None or cand[0] > best[0]:
            best = cand
    return best if best is not None else (0.0, "")


def country_adjust(country: str | None, ent: Entity) -> tuple[float, str]:
    if not country or not ent.nationalities:
        return 0.0, ""
    if country in ent.nationalities:
        return 0.02, f"country {country} is a listed nationality"
    return -0.03, f"country {country} not in listed nationalities ({', '.join(ent.nationalities)})"


# ----------------------------------------------------------------------------------------
# hits
# ----------------------------------------------------------------------------------------

@dataclass
class Hit:
    entity_id: str
    source: str
    type: str
    name: str
    matched_name: str
    matched_strength: str
    score: float
    programs: list[str] = field(default_factory=list)
    explanation: dict = field(default_factory=dict)

    @property
    def matched_alias(self) -> str | None:
        return None if self.matched_name == self.name else self.matched_name


def _score_record(
    q_tokens: list[str], q_phon: str, rec, ent: Entity, qdob: Dob | None,
    country: str | None, mode: str,
) -> tuple[float, dict]:
    ms = match.score_tokens(q_tokens, rec.tokens, q_phon, rec.phonetic, mode)
    score = ms.score
    explanation: dict = {
        "query_tokens": q_tokens,
        "candidate_tokens": rec.tokens,
        "sort_jw": ms.sort_jw,
        "coverage": ms.coverage,
        "phonetic": ms.phonetic,
        "base": ms.score,
        "mode": mode,
    }
    weak = rec.strength == "weak"
    if weak:
        score *= 0.95
        explanation["weak_alias_factor"] = 0.95

    d_delta, d_note = dob_adjust(qdob, ent)
    c_delta, c_note = country_adjust(country, ent)
    # a weak alias gets no boost from dob or country, penalties still count
    if weak:
        d_delta = min(d_delta, 0.0)
        c_delta = min(c_delta, 0.0)
    if d_note:
        explanation["dob"] = {"delta": d_delta, "note": d_note}
    if c_note:
        explanation["country"] = {"delta": c_delta, "note": c_note}
    score += d_delta + c_delta
    score = max(0.0, min(1.0, score))
    explanation["final"] = round(score, 4)
    return round(score, 4), explanation


def screen_name(
    index: Index,
    name: str,
    dob: str | None = None,
    country: str | None = None,
    threshold: float | None = None,
    mode: str = "balanced",
    customer_id: str | None = None,
    decisions_path: str | Path | None = None,
    limit: int | None = None,
    sources: list[str] | None = None,
) -> list[Hit]:
    """Screen one name. `threshold` is on the library scale, 0.0 - 1.0."""
    if threshold is None:
        threshold = config.DEFAULT_THRESHOLD
    if not 0.0 <= threshold <= 1.0:
        raise ValueError(f"threshold {threshold} is outside 0-1 (the CLI takes 0-100)")
    if mode not in match.MODES:
        raise ValueError(f"unknown mode {mode!r}")

    q_tokens = normalize.tokens(name)
    if len(" ".join(q_tokens)) < config.MIN_NAME_LENGTH:
        return []
    q_sorted = normalize.sort_key(q_tokens)
    q_phon = normalize.phonetic_key(q_tokens)
    qdob = parse_query_dob(dob)
    qcountry = query_country(country)

    best: dict[int, Hit] = {}
    for rec in index.records:
        pre = JaroWinkler.similarity(q_sorted, rec.sorted_key)
        if pre < config.CANDIDATE_FLOOR:
            continue
        ent = index.entities[rec.ent]
        score, explanation = _score_record(q_tokens, q_phon, rec, ent, qdob, qcountry, mode)
        if score < threshold:
            continue
        if ent.type in ("vessel", "aircraft") and score < config.VESSEL_MIN_SCORE:
            continue
        current = best.get(rec.ent)
        if current is not None and current.score >= score:
            continue
        best[rec.ent] = Hit(
            entity_id=ent.id, source=ent.source, type=ent.type, name=ent.name,
            matched_name=rec.name, matched_strength=rec.strength, score=score,
            programs=list(ent.programs), explanation=explanation,
        )

    hits = sorted(best.values(), key=lambda h: (-h.score, h.entity_id))
    hits = _drop_decided(hits, customer_id, name, decisions_path)
    hits = filter_hits(hits, sources=sources)
    cap = limit if limit is not None else config.MAX_HITS
    hits = hits[:cap]
    link_related(hits, index)
    return hits


def _drop_decided(
    hits: list[Hit], customer_id: str | None, name: str, decisions_path: str | Path | None
) -> list[Hit]:
    if decisions_path is None or not hits:
        return hits
    pairs = decisions_mod.suppressed_pairs(decisions_mod.load_decisions(decisions_path))
    if not pairs:
        return hits
    ref = decisions_mod.customer_ref(customer_id, name)
    return [h for h in hits if (ref, h.entity_id) not in pairs]


# ----------------------------------------------------------------------------------------
# customers
# ----------------------------------------------------------------------------------------

_NAME_COLUMNS = ("name", "customer_name", "full_name")
_DOB_COLUMNS = ("dob", "date_of_birth", "birth_date", "birthdate")
_COUNTRY_COLUMNS = ("country", "nationality", "country_code")
_ID_COLUMNS = ("customer_id", "id", "ref", "reference")


def _pick(row: dict[str, str], candidates: tuple[str, ...]) -> str | None:
    for c in candidates:
        if c in row and row[c] and row[c].strip():
            return row[c].strip()
    return None


def read_customers(path: str | Path) -> list[Query]:
    """CSV with at least a name column. dob, country and an id column are optional."""
    out: list[Query] = []
    with open(path, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        if reader.fieldnames is None:
            return out
        reader.fieldnames = [f.strip().lower() for f in reader.fieldnames]
        if not any(c in reader.fieldnames for c in _NAME_COLUMNS):
            raise ValueError(f"{path}: no name column (looked for {', '.join(_NAME_COLUMNS)})")
        for row in reader:
            name = _pick(row, _NAME_COLUMNS)
            if not name:
                continue
            out.append(Query(
                name=name, dob=_pick(row, _DOB_COLUMNS), country=_pick(row, _COUNTRY_COLUMNS),
                customer_id=_pick(row, _ID_COLUMNS),
            ))
    return out


def screen_customers(
    index: Index,
    queries: list[Query],
    threshold: float | None = None,
    mode: str = "balanced",
    decisions_path: str | Path | None = None,
) -> list[tuple[Query, list[Hit]]]:
    results = []
    for q in queries:
        hits = screen_name(
            index, q.name, dob=q.dob, country=q.country, threshold=threshold, mode=mode,
            customer_id=q.customer_id, decisions_path=decisions_path,
        )
        results.append((q, hits))
    return results


# ----------------------------------------------------------------------------------------
# output
# ----------------------------------------------------------------------------------------

def hit_to_dict(hit: Hit, with_explanation: bool = True) -> dict:
    out = {
        "entity_id": hit.entity_id,
        "source": hit.source,
        "type": hit.type,
        "name": hit.name,
        "matched_alias": hit.matched_alias,
        "matched_strength": hit.matched_strength,
        "score": hit.score,
        "programs": hit.programs,
    }
    if with_explanation:
        out["explanation"] = hit.explanation
    return out


def format_hits(hits: list[Hit], verbose: bool = True) -> str:
    """Plain text table for the terminal."""
    if not hits:
        return "no hits above threshold"
    lines = []
    for i, h in enumerate(hits, 1):
        via = f" via alias '{h.matched_name}'" if h.matched_alias else ""
        if h.matched_strength == "weak" and h.matched_alias:
            via += " (weak)"
        label = f"{confidence_label(h.score)}/{review_priority(h)}"
        lines.append(
            f"{i:>2}. {h.score:.3f}  {h.entity_id:<14} {h.type:<12} {h.name}{via}  [{label}]"
        )
        if not verbose:
            continue
        ex = h.explanation
        if "also_listed_as" in ex:
            lines.append(f"      same party as: {', '.join(ex['also_listed_as'])}")
        lines.append(
            f"      names: sort={ex['sort_jw']:.3f} coverage={ex['coverage']:.3f} "
            f"phonetic={ex['phonetic']:.3f} -> base {ex['base']:.3f}"
        )
        if "weak_alias_factor" in ex:
            lines.append(f"      weak alias: x{ex['weak_alias_factor']}")
        if "dob" in ex:
            lines.append(f"      dob: {ex['dob']['delta']:+.2f} ({ex['dob']['note']})")
        if "country" in ex:
            lines.append(f"      country: {ex['country']['delta']:+.2f} ({ex['country']['note']})")
        if h.programs:
            lines.append(f"      programs: {', '.join(h.programs)}")
    return "\n".join(lines)


def hits_to_json(hits: list[Hit]) -> str:
    return json.dumps([hit_to_dict(h) for h in hits], ensure_ascii=False, indent=2)


def summarize(results: list[tuple[Query, list[Hit]]]) -> dict:
    flagged = [r for r in results if r[1]]
    by_source: dict[str, int] = {}
    for _q, hits in flagged:
        for h in hits:
            by_source[h.source] = by_source.get(h.source, 0) + 1
    return {
        "rows": len(results),
        "rows_with_hits": len(flagged),
        "total_hits": sum(len(h) for _q, h in flagged),
        "hits_by_source": dict(sorted(by_source.items())),
        "most_hit_entities": [{"entity_id": e, "customers": n} for e, n in top_entities(results)],
    }


def hits_to_csv(hits: list[Hit]) -> str:
    out = io.StringIO()
    w = csv.writer(out, lineterminator="\n")
    w.writerow(
        ["rank", "score", "entity_id", "source", "type", "name", "matched_alias", "programs"]
    )
    for i, h in enumerate(hits, 1):
        w.writerow([i, h.score, h.entity_id, h.source, h.type, h.name, h.matched_alias or "",
                    ";".join(h.programs)])
    return out.getvalue()


def hits_to_markdown(hits: list[Hit]) -> str:
    if not hits:
        return "_no hits above threshold_"
    lines = ["| # | score | id | type | name | via alias |", "|---|---|---|---|---|---|"]
    for i, h in enumerate(hits, 1):
        lines.append(
            f"| {i} | {h.score:.3f} | {h.entity_id} | {h.type} | {h.name} "
            f"| {h.matched_alias or ''} |"
        )
    return "\n".join(lines)


# ----------------------------------------------------------------------------------------
# bands, filters, related hits
# ----------------------------------------------------------------------------------------

def confidence_label(score: float) -> str:
    if score >= config.BAND_STRONG:
        return "strong"
    if score >= config.BAND_LIKELY:
        return "likely"
    return "possible"


def filter_hits(
    hits: list[Hit],
    sources: list[str] | None = None,
    types: list[str] | None = None,
    min_score: float | None = None,
) -> list[Hit]:
    out = hits
    if sources:
        wanted = {s.lower() for s in sources}
        out = [h for h in out if h.source in wanted]
    if types:
        wanted_t = {t.lower() for t in types}
        out = [h for h in out if h.type in wanted_t]
    if min_score is not None:
        out = [h for h in out if h.score >= min_score]
    return out


def _doc_numbers(ent: Entity) -> set[str]:
    return {re.sub(r"\W+", "", d.number).upper() for d in ent.documents if d.number}


def _same_party(a: Entity, b: Entity) -> bool:
    """Do two list entries look like the same real-world party?"""
    if a.id == b.id or a.type != b.type:
        return False
    if _doc_numbers(a) & _doc_numbers(b):
        return True
    ka = normalize.sort_key(normalize.tokens(a.name))
    kb = normalize.sort_key(normalize.tokens(b.name))
    if JaroWinkler.similarity(ka, kb) < config.RELATED_NAME_MIN:
        return False
    if a.nationalities and b.nationalities and not set(a.nationalities) & set(b.nationalities):
        return False
    years_a = {d.year for d in a.dobs if d.year}
    years_b = {d.year for d in b.dobs if d.year}
    if years_a and years_b and not years_a & years_b:
        return False
    return True


def link_related(hits: list[Hit], index: Index) -> None:
    """Mark hits that are probably the same party listed by several sources."""
    ents = {h.entity_id: index.entity_by_id(h.entity_id) for h in hits}
    for a in hits:
        ea = ents[a.entity_id]
        if ea is None:
            continue
        related = [
            b.entity_id for b in hits
            if (eb := ents[b.entity_id]) is not None and _same_party(ea, eb)
        ]
        if related:
            a.explanation["also_listed_as"] = related


def screen_stream(
    index: Index,
    queries: list[Query],
    threshold: float | None = None,
    mode: str = "balanced",
    decisions_path: str | Path | None = None,
    on_row=None,
):
    """Like screen_customers but yields row by row, with an optional progress callback."""
    for i, q in enumerate(queries, 1):
        hits = screen_name(
            index, q.name, dob=q.dob, country=q.country, threshold=threshold, mode=mode,
            customer_id=q.customer_id, decisions_path=decisions_path,
        )
        if on_row is not None:
            on_row(i, len(queries), q, hits)
        yield q, hits


# ----------------------------------------------------------------------------------------
# diagnostics
# ----------------------------------------------------------------------------------------

def describe_query(name: str) -> dict:
    """What the matcher sees for a name. Handy when a hit is missing."""
    toks = normalize.tokens(name)
    return {
        "input": name,
        "normalized_text": normalize.normalize_text(name),
        "tokens": toks,
        "sort_key": normalize.sort_key(toks),
        "phonetic": normalize.phonetic_key(toks),
    }


def describe_index(index: Index) -> dict:
    by_source: dict[str, int] = {}
    by_type: dict[str, int] = {}
    dates: dict[str, str] = {}
    for ent in index.entities:
        by_source[ent.source] = by_source.get(ent.source, 0) + 1
        by_type[ent.type] = by_type.get(ent.type, 0) + 1
        if ent.list_date and ent.list_date > dates.get(ent.source, ""):
            dates[ent.source] = ent.list_date
    weak = sum(1 for r in index.records if r.strength == "weak")
    return {
        "entities": len(index.entities),
        "names": len(index.records),
        "weak_alias_names": weak,
        "by_source": dict(sorted(by_source.items())),
        "by_type": dict(sorted(by_type.items())),
        "list_dates": dict(sorted(dates.items())),
        "built_at": index.built_at,
    }


def duplicate_ids(entities: list[Entity]) -> list[str]:
    seen: set[str] = set()
    dup: list[str] = []
    for e in entities:
        if e.id in seen:
            dup.append(e.id)
        seen.add(e.id)
    return dup


def clear_cache() -> None:
    _INDEX_CACHE.clear()


def stale_sources(index: Index, today: date | None = None) -> dict[str, int]:
    """Sources whose list is older than config.STALE_LIST_DAYS, with the age in days."""
    today = today or date.today()
    newest: dict[str, str] = {}
    for ent in index.entities:
        if ent.list_date and ent.list_date > newest.get(ent.source, ""):
            newest[ent.source] = ent.list_date
    stale: dict[str, int] = {}
    for source, iso in newest.items():
        try:
            age = (today - date.fromisoformat(iso[:10])).days
        except ValueError:
            continue
        if age > config.STALE_LIST_DAYS:
            stale[source] = age
    return dict(sorted(stale.items()))


# ----------------------------------------------------------------------------------------
# review helpers
# ----------------------------------------------------------------------------------------

# programs that make a hit worth looking at first. Not exhaustive, just what we see most.
_HIGH_RISK_PROGRAMS = {"SDGT", "SDT", "IRGC", "DPRK3", "Al-Qaida", "Taliban", "TAL", "PRK"}


def review_priority(hit: Hit) -> str:
    risky = any(p in _HIGH_RISK_PROGRAMS for p in hit.programs)
    label = confidence_label(hit.score)
    if label == "strong" and risky:
        return "high"
    if label == "possible" and not risky:
        return "low"
    return "medium"


def explain_hit(hit: Hit) -> str:
    """One paragraph a reviewer can read without knowing how the score is built."""
    ex = hit.explanation
    parts = [f"{hit.score:.0%} match with {hit.name} ({hit.entity_id}, {hit.type})."]
    if hit.matched_alias:
        kind = "weak " if hit.matched_strength == "weak" else ""
        parts.append(f"The name that matched is the {kind}alias '{hit.matched_alias}'.")
    if "sort_jw" in ex:
        parts.append(
            f"The names are {ex['sort_jw']:.0%} alike regardless of word order and "
            f"{ex['coverage']:.0%} of their words have a close partner."
        )
    if "dob" in ex:
        delta = ex["dob"]["delta"]
        verb = "supports" if delta > 0 else "counts against" if delta < 0 else "does not change"
        parts.append(f"The date of birth {verb} the match ({ex['dob']['note']}).")
    if "country" in ex:
        verb = "supports" if ex["country"]["delta"] > 0 else "counts against"
        parts.append(f"The country {verb} the match ({ex['country']['note']}).")
    if "also_listed_as" in ex:
        parts.append(f"Probably the same party as {', '.join(ex['also_listed_as'])}.")
    return " ".join(parts)


def top_entities(results: list[tuple[Query, list[Hit]]], n: int = 5) -> list[tuple[str, int]]:
    """Entities that hit the most customers. A list entry matching dozens of rows is usually
    a common name, not dozens of true positives."""
    counts: dict[str, int] = {}
    for _q, hits in results:
        for h in hits:
            counts[h.entity_id] = counts.get(h.entity_id, 0) + 1
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    return ranked[:n]


def band_counts(results: list[tuple[Query, list[Hit]]]) -> dict[str, int]:
    """How many hits fall in each confidence band, for the top hit of every flagged row."""
    counts: dict[str, int] = {}
    for _q, hits in results:
        if not hits:
            continue
        label = confidence_label(hits[0].score)
        counts[label] = counts.get(label, 0) + 1
    return dict(sorted(counts.items()))


def programs_summary(
    results: list[tuple[Query, list[Hit]]], limit: int = 10
) -> list[tuple[str, int]]:
    """Most common sanctions programs across all hits, handy to eyeball a batch."""
    seen: dict[str, int] = {}
    for _q, hits in results:
        for h in hits:
            for prog in h.programs:
                seen[prog] = seen.get(prog, 0) + 1
    ranked = sorted(seen.items(), key=lambda kv: (-kv[1], kv[0]))
    return ranked[:limit]
