from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Union


@dataclass
class Column:
    name: str


@dataclass
class Literal:
    value: Any            # int | float | str | bool | None


Operand = Union[Column, Literal]


@dataclass
class Comparison:
    left: Operand
    op: str               # = != < > <= >=
    right: Operand


@dataclass
class And:
    left: "Condition"
    right: "Condition"


@dataclass
class Or:
    left: "Condition"
    right: "Condition"


@dataclass
class Not:
    operand: "Condition"


@dataclass
class InList:
    operand: Operand
    values: list[Any]
    negated: bool = False


@dataclass
class InSubquery:
    operand: Operand
    query: "Query"
    negated: bool = False


Condition = Union[Comparison, And, Or, Not, InList, InSubquery]


@dataclass
class TableRef:
    name: str


@dataclass
class Select:
    condition: Condition
    child: "Query"


@dataclass
class Project:
    columns: list[str]
    child: "Query"


@dataclass
class Join:
    left: "Query"
    right: "Query"
    condition: Condition | None = None     # None -> natural join


@dataclass
class Union_:
    left: "Query"
    right: "Query"


@dataclass
class Intersect:
    left: "Query"
    right: "Query"


@dataclass
class Difference:
    left: "Query"
    right: "Query"


@dataclass
class AggSpec:
    func: str                              # COUNT SUM AVG MIN MAX
    column: str | None                     # None means '*'
    alias: str | None = None

    def output_name(self) -> str:
        if self.alias:
            return self.alias
        return f"{self.func}({self.column or '*'})"


@dataclass
class Aggregate:
    group_by: list[str]
    aggregates: list[AggSpec]
    child: "Query"


@dataclass
class Rename:
    mapping: list[tuple[str, str]]         # (old, new)
    child: "Query"


Query = Union[TableRef, Select, Project, Join, Union_, Intersect, Difference, Aggregate, Rename]