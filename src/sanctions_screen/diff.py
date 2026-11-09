"""What changed between two snapshots of the lists."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from .model import Entity
from .screen import load_lists, load_one


@dataclass
class EntityChange:
    id: str
    name: str
    fields: dict[str, tuple[list[str], list[str]]] = field(default_factory=dict)


@dataclass
class DiffResult:
    sources: list[str]
    added: list[Entity]
    removed: list[Entity]
    changed: list[EntityChange]

    @property
    def total(self) -> int:
        return len(self.added) + len(self.removed) + len(self.changed)


def _fingerprint(ent: Entity) -> dict[str, list[str]]:
    return {
        "name": [ent.name],
        "type": [ent.type],
        "aliases": sorted(f"{a.name} ({a.strength})" for a in ent.aliases),
        "dobs": sorted(d.label() for d in ent.dobs),
        "nationalities": sorted(ent.nationalities),
        "documents": sorted(f"{d.kind} {d.number}" for d in ent.documents),
        "programs": sorted(ent.programs),
    }


def diff_entities(old: list[Entity], new: list[Entity]) -> DiffResult:
    old_by_id = {e.id: e for e in old}
    new_by_id = {e.id: e for e in new}
    added = [new_by_id[i] for i in sorted(new_by_id.keys() - old_by_id.keys())]
    removed = [old_by_id[i] for i in sorted(old_by_id.keys() - new_by_id.keys())]
    changed: list[EntityChange] = []
    for ent_id in sorted(old_by_id.keys() & new_by_id.keys()):
        a, b = _fingerprint(old_by_id[ent_id]), _fingerprint(new_by_id[ent_id])
        delta = {k: (a[k], b[k]) for k in a if a[k] != b[k]}
        if delta:
            changed.append(EntityChange(ent_id, new_by_id[ent_id].name, delta))
    sources = sorted({e.source for e in old} | {e.source for e in new})
    return DiffResult(sources, added, removed, changed)


def _load(path: Path) -> list[Entity]:
    return load_lists(path) if path.is_dir() else load_one(path)


def diff_paths(old: str | Path, new: str | Path) -> DiffResult:
    """Each side is a directory of lists or one list file. Only sources present on both
    sides are compared, otherwise every entity of a missing list would show up as added."""
    old_ents, new_ents = _load(Path(old)), _load(Path(new))
    common = {e.source for e in old_ents} & {e.source for e in new_ents}
    return diff_entities(
        [e for e in old_ents if e.source in common],
        [e for e in new_ents if e.source in common],
    )


def format_diff(result: DiffResult, verbose: bool = True) -> str:
    lines = [
        f"sources compared: {', '.join(result.sources) or '-'}",
        f"added {len(result.added)}, removed {len(result.removed)}, changed {len(result.changed)}",
    ]
    for e in result.added:
        lines.append(f"+ {e.id:<14} {e.name}")
    for e in result.removed:
        lines.append(f"- {e.id:<14} {e.name}")
    for c in result.changed:
        lines.append(f"~ {c.id:<14} {c.name}")
        if verbose:
            for key, (before, after) in c.fields.items():
                lines.append(f"    {key}: {before} -> {after}")
    return "\n".join(lines)


def diff_to_json(result: DiffResult) -> str:
    doc = {
        "sources": result.sources,
        "added": [e.id for e in result.added],
        "removed": [e.id for e in result.removed],
        "changed": [
            {
                "id": c.id,
                "name": c.name,
                "fields": {k: {"old": v[0], "new": v[1]} for k, v in c.fields.items()},
            }
            for c in result.changed
        ],
    }
    return json.dumps(doc, ensure_ascii=False, indent=2)
