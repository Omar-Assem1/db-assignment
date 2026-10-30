from __future__ import annotations

import operators as ops
from ast_nodes import (Aggregate, And, Column, Comparison, Difference, InList, InSubquery,
                       Intersect, Join, Literal, Not, Or, Project, Rename, Select,
                       TableRef, Union_)
from errors import QueryError
from operators import Relation
from parser import parse


def _compare(a, op, b) -> bool:
    if op == "=":
        return a == b
    if op == "!=":
        return a != b
    if a is None or b is None:
        return False
    try:
        return {"<": a < b, ">": a > b, "<=": a <= b, ">=": a >= b}[op]
    except TypeError:
        raise QueryError(f"Cannot compare {a!r} {op} {b!r}") from None


def _cond_columns(c) -> set[str]:
    if isinstance(c, Comparison):
        return {o.name for o in (c.left, c.right) if isinstance(o, Column)}
    if isinstance(c, (And, Or)):
        return _cond_columns(c.left) | _cond_columns(c.right)
    if isinstance(c, Not):
        return _cond_columns(c.operand)
    if isinstance(c, (InList, InSubquery)):
        return {c.operand.name} if isinstance(c.operand, Column) else set()
    return set()


class Executor:
    def __init__(self, tables: dict[str, Relation]):
        self.tables = tables

    def run_text(self, text: str) -> Relation:
        return self.run(parse(text))

    def run(self, q) -> Relation:
        if isinstance(q, TableRef):
            if q.name not in self.tables:
                raise QueryError(f"Unknown table '{q.name}' (available: {', '.join(self.tables)})")
            return self.tables[q.name]
        if isinstance(q, Select):
            rel = self.run(q.child)
            self._check_cols(q.condition, rel)
            return ops.select(rel, self._predicate(q.condition))
        if isinstance(q, Project):
            return ops.project(self.run(q.child), q.columns)
        if isinstance(q, Join):
            left, right = self.run(q.left), self.run(q.right)
            if q.condition is None:
                return ops.natural_join(left, right)
            self._check_cols(q.condition, Relation(left.columns + right.columns, []))
            return ops.theta_join(left, right, self._predicate(q.condition))
        if isinstance(q, Union_):
            return ops.union(self.run(q.left), self.run(q.right))
        if isinstance(q, Intersect):
            return ops.intersect(self.run(q.left), self.run(q.right))
        if isinstance(q, Difference):
            return ops.difference(self.run(q.left), self.run(q.right))
        if isinstance(q, Aggregate):
            return ops.aggregate(self.run(q.child), q.group_by, q.aggregates)
        if isinstance(q, Rename):
            return ops.rename(self.run(q.child), q.mapping)
        raise QueryError(f"Unsupported query node {type(q).__name__}")

    # ---- conditions ----
    @staticmethod
    def _check_cols(cond, rel: Relation) -> None:
        for c in _cond_columns(cond):
            rel.index(c)

    def _predicate(self, cond):
        subsets: dict[int, set] = {}          # evaluate each subquery only once

        def val(o, row):
            return row[o.name] if isinstance(o, Column) else o.value

        def ev(c, row) -> bool:
            if isinstance(c, Comparison):
                return _compare(val(c.left, row), c.op, val(c.right, row))
            if isinstance(c, And):
                return ev(c.left, row) and ev(c.right, row)
            if isinstance(c, Or):
                return ev(c.left, row) or ev(c.right, row)
            if isinstance(c, Not):
                return not ev(c.operand, row)
            if isinstance(c, InList):
                return (val(c.operand, row) in c.values) != c.negated
            if isinstance(c, InSubquery):
                if id(c) not in subsets:
                    sub = self.run(c.query)
                    if len(sub.columns) != 1:
                        raise QueryError("Subquery in IN must return exactly one column")
                    subsets[id(c)] = {r[0] for r in sub.rows}
                return (val(c.operand, row) in subsets[id(c)]) != c.negated
            raise QueryError(f"Unsupported condition {type(c).__name__}")

        return lambda row: ev(cond, row)