"""Blocking by phonetic key, to avoid scanning every name on every query.

Work in progress. The block lookup works; scoring on top of it is not wired up, and it
has not been compared against the linear scan yet, so nothing imports this module.
"""

from __future__ import annotations

from collections import defaultdict

import jellyfish

from .index import Index


class BlockedIndex:
    def __init__(self, index: Index) -> None:
        self.index = index
        self.blocks: dict[str, list[int]] = defaultdict(list)
        for pos, rec in enumerate(index.records):
            for tok in rec.tokens:
                key = jellyfish.metaphone(tok)
                if key:
                    self.blocks[key].append(pos)

    def candidates(self, query_tokens: list[str]) -> list[int]:
        """Record positions sharing at least one phonetic token key with the query."""
        found: set[int] = set()
        for tok in query_tokens:
            found.update(self.blocks.get(jellyfish.metaphone(tok), ()))
        return sorted(found)

    def stats(self) -> dict[str, float]:
        sizes = [len(v) for v in self.blocks.values()]
        if not sizes:
            return {"blocks": 0, "mean": 0.0, "max": 0}
        return {"blocks": len(sizes), "mean": sum(sizes) / len(sizes), "max": max(sizes)}


def screen_blocked(blocked: BlockedIndex, name: str):
    # TODO: score only blocked.candidates(...) with match.score_tokens, then share the
    # boost/decision code with screen.py (it's inline there, needs pulling out first).
    # TODO: single-token blocks for very common tokens (Mohammed, Silva) are huge,
    # need a cap or a second key.
    raise NotImplementedError("blocked screening is not finished")
