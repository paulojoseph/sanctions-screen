"""Unified entity model shared by every list parser."""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

EntityType = Literal["person", "organization", "vessel", "aircraft"]
AliasStrength = Literal["strong", "weak"]
DobKind = Literal["full", "year", "circa", "range"]


class Alias(BaseModel):
    name: str
    # strong = "a.k.a." / good quality, weak = "f.k.a." / low quality
    # NOTE: weak aliases ARE scored (see Alias handling in screen.py), just not boosted.
    strength: AliasStrength = "strong"


class Dob(BaseModel):
    """A date of birth as the lists publish it: not always a real date."""

    kind: DobKind
    year: int | None = None
    month: int | None = None
    day: int | None = None
    year_to: int | None = None  # only for kind == "range"

    def as_date(self) -> date | None:
        if self.year is None:
            return None
        return date(self.year, self.month or 1, self.day or 1)

    def label(self) -> str:
        if self.kind == "full" and self.month and self.day:
            return f"{self.year:04d}-{self.month:02d}-{self.day:02d}"
        if self.kind == "range" and self.year_to:
            return f"{self.year}-{self.year_to}"
        if self.kind == "circa":
            return f"circa {self.year}"
        return str(self.year)


class IdDocument(BaseModel):
    kind: str
    number: str
    country: str | None = None


class Entity(BaseModel):
    id: str  # "source:uid", stable, the decisions file depends on it
    source: str
    uid: str
    type: EntityType
    name: str
    aliases: list[Alias] = Field(default_factory=list)
    dobs: list[Dob] = Field(default_factory=list)
    nationalities: list[str] = Field(default_factory=list)  # ISO 3166 alpha-2
    documents: list[IdDocument] = Field(default_factory=list)
    programs: list[str] = Field(default_factory=list)
    list_date: str | None = None  # publish date of the list this came from, ISO

    def all_names(self) -> list[tuple[str, str]]:
        """(name, strength) for the primary name and every alias, primary first."""
        out = [(self.name, "strong")]
        out.extend((a.name, a.strength) for a in self.aliases)
        return out


def make_id(source: str, uid: str) -> str:
    return f"{source}:{uid}"
