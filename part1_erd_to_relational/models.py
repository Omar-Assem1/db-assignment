
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Attribute:
    name: str
    is_primary_key: bool = False
    is_partial_key: bool = False      # discriminator of a weak entity
    is_multi_valued: bool = False
    composite: list[str] = field(default_factory=list)

    def flat_names(self) -> list[str]:
        return list(self.composite) if self.composite else [self.name]


@dataclass
class Entity:
    name: str
    attributes: list[Attribute]
    is_weak: bool = False
    owner: str | None = None          # identifying (owner) entity for weak entities


@dataclass
class Relationship:
    name: str
    entity1: str
    entity2: str
    cardinality: str                  # normalized: "1:1", "1:N", "N:1", "M:N"
    attributes: list[Attribute] = field(default_factory=list)
    participation1: str = "partial"   # "total" | "partial" (for entity1)
    participation2: str = "partial"   # (for entity2)


@dataclass
class Column:
    name: str
    is_pk: bool = False
    is_fk: bool = False


@dataclass
class ForeignKey:
    columns: list[str]
    ref_table: str
    ref_columns: list[str]


@dataclass
class Table:
    name: str
    columns: list[Column] = field(default_factory=list)
    foreign_keys: list[ForeignKey] = field(default_factory=list)

    def has_column(self, name: str) -> bool:
        return any(c.name == name for c in self.columns)

    def add_column(self, col: Column, index: int | None = None) -> None:
        if self.has_column(col.name):
            raise ValueError(f"Duplicate column '{col.name}' in table '{self.name}'")
        if index is None:
            self.columns.append(col)
        else:
            self.columns.insert(index, col)

    def pk_names(self) -> list[str]:
        return [c.name for c in self.columns if c.is_pk]

    def to_text(self) -> str:
        refs = {}
        for fk in self.foreign_keys:
            for c, rc in zip(fk.columns, fk.ref_columns):
                refs[c] = f"{fk.ref_table}.{rc}"
        lines = [self.name]
        for c in self.columns:
            tag = ",".join(t for t, on in (("PK", c.is_pk), ("FK", c.is_fk)) if on)
            line = f"  {c.name}"
            if tag:
                line += f"  [{tag}]"
            if c.name in refs:
                line += f" -> {refs[c.name]}"
            lines.append(line)
        return "\n".join(lines)