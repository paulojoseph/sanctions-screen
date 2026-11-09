"""Local index: entities plus one precomputed record per name, kept in a gzipped JSON file.

Written before normalize.py grew its own tokenizer, hence the small helper below.
TODO: replace _index_tokens with normalize.tokens and rebuild the index files.
"""

from __future__ import annotations

import gzip
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from . import __version__
from .model import Entity
from .normalize import (
    LEGAL_FORMS,
    drop_iberian_particles,
    normalize_text,
    phonetic_key,
    sort_key,
)

INDEX_FORMAT = 2

_TITLES = {"mr", "mrs", "dr", "sheikh", "shaikh", "hajji", "haji", "general", "colonel"}
_PARTICLES = {"al", "el", "bin", "ibn", "bint", "ben"}


@dataclass
class NameRecord:
    ent: int  # position in Index.entities
    name: str
    strength: str
    tokens: list[str]
    sorted_key: str
    phonetic: str


@dataclass
class Index:
    entities: list[Entity]
    records: list[NameRecord]
    built_at: str
    version: str = __version__

    def entity_by_id(self, entity_id: str) -> Entity | None:
        for ent in self.entities:
            if ent.id == entity_id:
                return ent
        return None

    @property
    def sources(self) -> list[str]:
        return sorted({e.source for e in self.entities})


def _index_tokens(name: str) -> list[str]:
    toks = [t for t in normalize_text(name).split(" ") if t]
    while len(toks) > 1 and toks[0] in _TITLES:
        toks = toks[1:]
    end = len(toks)
    while end > 1 and toks[end - 1] in LEGAL_FORMS:
        end -= 1
    toks = toks[:end]
    # particles never carry the match on their own
    kept = [t for t in toks if t not in _PARTICLES]
    toks = kept or toks
    return drop_iberian_particles(toks)


def build_index(entities: list[Entity]) -> Index:
    records: list[NameRecord] = []
    for pos, ent in enumerate(entities):
        seen: set[str] = set()
        for name, strength in ent.all_names():
            toks = _index_tokens(name)
            if not toks:
                continue
            key = " ".join(toks)
            if key in seen:
                continue
            seen.add(key)
            records.append(NameRecord(
                ent=pos, name=name, strength=strength, tokens=toks,
                sorted_key=sort_key(toks), phonetic=phonetic_key(toks),
            ))
    return Index(entities, records, datetime.now(timezone.utc).isoformat(timespec="seconds"))


def save_index(idx: Index, path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "format": INDEX_FORMAT,
        "version": idx.version,
        "built_at": idx.built_at,
        "entities": [e.model_dump() for e in idx.entities],
        "records": [asdict(r) for r in idx.records],
    }
    with gzip.open(path, "wt", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False)


def load_index(path: str | Path) -> Index:
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        payload = json.load(fh)
    if payload.get("format") != INDEX_FORMAT:
        raise ValueError(
            f"{path}: index format {payload.get('format')} is not {INDEX_FORMAT}, run `index` again"
        )
    return Index(
        entities=[Entity.model_validate(e) for e in payload["entities"]],
        records=[NameRecord(**r) for r in payload["records"]],
        built_at=payload["built_at"],
        version=payload.get("version", "?"),
    )
