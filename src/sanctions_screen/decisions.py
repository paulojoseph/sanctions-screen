"""Reviewer decisions: "this customer is not that listed entity".

One JSON object per line. The key is (customer_ref, entity_id), and entity ids are
`source:uid`, so a decision keeps working when the list is re-downloaded.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from .normalize import normalize

NOT_A_MATCH = "not_a_match"


@dataclass(frozen=True)
class Decision:
    customer_ref: str
    entity_id: str
    decision: str
    reviewer: str
    reason: str
    decided_at: str


def customer_ref(customer_id: str | None, name: str) -> str:
    """Rows without an id are identified by their normalized name."""
    if customer_id:
        return customer_id
    return "name:" + normalize(name)


def load_decisions(path: str | Path | None) -> list[Decision]:
    if path is None or not Path(path).exists():
        return []
    out: list[Decision] = []
    with open(path, encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                out.append(Decision(**json.loads(line)))
            except (json.JSONDecodeError, TypeError) as exc:
                raise ValueError(f"{path}:{lineno}: bad decision line ({exc})") from exc
    return out


def suppressed_pairs(decisions: list[Decision]) -> set[tuple[str, str]]:
    return {(d.customer_ref, d.entity_id) for d in decisions if d.decision == NOT_A_MATCH}


def append_decision(
    path: str | Path, ref: str, entity_id: str, reviewer: str, reason: str
) -> Decision:
    dec = Decision(
        customer_ref=ref, entity_id=entity_id, decision=NOT_A_MATCH, reviewer=reviewer,
        reason=reason, decided_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
    )
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(asdict(dec), ensure_ascii=False) + "\n")
    return dec
