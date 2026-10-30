from __future__ import annotations

from errors import QueryError


class Relation:

    def __init__(self, columns: list[str], rows: list[tuple]):
        if len(set(columns)) != len(columns):
            raise QueryError(f"Duplicate column names in relation: {columns}")
        self.columns = list(columns)
        self.rows = [tuple(r) for r in rows]

    def index(self, col: str) -> int:
        try:
            return self.columns.index(col)
        except ValueError:
            raise QueryError(f"Unknown column '{col}' (available: {', '.join(self.columns)})") from None

    def dicts(self):
        return (dict(zip(self.columns, r)) for r in self.rows)


def _dedupe(rows):
    return list(dict.fromkeys(rows))


def select(rel: Relation, pred) -> Relation:
    return Relation(rel.columns, [r for r, d in zip(rel.rows, rel.dicts()) if pred(d)])


def project(rel: Relation, cols: list[str]) -> Relation:
    if len(set(cols)) != len(cols):
        raise QueryError(f"Duplicate column in PROJECT: {cols}")
    idx = [rel.index(c) for c in cols]
    return Relation(cols, _dedupe(tuple(r[i] for i in idx) for r in rel.rows))


def rename(rel: Relation, mapping: list[tuple[str, str]]) -> Relation:
    m = dict(mapping)
    for old in m:
        rel.index(old)
    return Relation([m.get(c, c) for c in rel.columns], rel.rows)


def natural_join(left: Relation, right: Relation) -> Relation:
    common = [c for c in left.columns if c in right.columns]
    extra = [c for c in right.columns if c not in common]
    li = [left.index(c) for c in common]
    ri = [right.index(c) for c in common]
    ei = [right.index(c) for c in extra]

    buckets: dict[tuple, list[tuple]] = {}
    for r in right.rows:
        key = tuple(r[i] for i in ri)
        if None in key:                      # NULL never matches
            continue
        buckets.setdefault(key, []).append(r)

    out = []
    for l in left.rows:
        key = tuple(l[i] for i in li)
        if None in key:
            continue
        for r in buckets.get(key, []):
            out.append(l + tuple(r[i] for i in ei))
    return Relation(left.columns + extra, _dedupe(out))


def theta_join(left: Relation, right: Relation, pred) -> Relation:
    clash = [c for c in left.columns if c in right.columns]
    if clash:
        raise QueryError(f"Theta join has clashing columns {clash}; use RENAME first")
    cols = left.columns + right.columns
    out = [l + r for l in left.rows for r in right.rows if pred(dict(zip(cols, l + r)))]
    return Relation(cols, out)


def _align(left: Relation, right: Relation, op: str) -> Relation:
    if sorted(left.columns) != sorted(right.columns):
        raise QueryError(f"{op} needs the same columns: {left.columns} vs {right.columns}")
    idx = [right.index(c) for c in left.columns]
    return Relation(left.columns, [tuple(r[i] for i in idx) for r in right.rows])


def union(left: Relation, right: Relation) -> Relation:
    right = _align(left, right, "UNION")
    return Relation(left.columns, _dedupe(left.rows + right.rows))


def intersect(left: Relation, right: Relation) -> Relation:
    right = _align(left, right, "INTERSECT")
    keep = set(right.rows)
    return Relation(left.columns, _dedupe(r for r in left.rows if r in keep))


def difference(left: Relation, right: Relation) -> Relation:
    right = _align(left, right, "DIFFERENCE")
    drop = set(right.rows)
    return Relation(left.columns, _dedupe(r for r in left.rows if r not in drop))


def _agg_value(func: str, values: list, n_rows: int, star: bool):
    if func == "COUNT":
        return n_rows if star else len(values)
    vals = [v for v in values if v is not None]
    if not vals:
        return None
    try:
        if func == "SUM":
            return sum(vals)
        if func == "AVG":
            return sum(vals) / len(vals)
        if func == "MIN":
            return min(vals)
        if func == "MAX":
            return max(vals)
    except TypeError:
        raise QueryError(f"{func} cannot be applied to these values: {vals[:3]}...") from None
    raise QueryError(f"Unknown aggregate function '{func}'")


def aggregate(rel: Relation, group_by: list[str], specs) -> Relation:
    gi = [rel.index(c) for c in group_by]
    cols = [None if s.column is None else rel.index(s.column) for s in specs]
    for s in specs:
        if s.column is None and s.func != "COUNT":
            raise QueryError(f"{s.func}(*) is not allowed; only COUNT(*)")

    groups: dict[tuple, list[tuple]] = {}
    for r in rel.rows:
        groups.setdefault(tuple(r[i] for i in gi), []).append(r)
    if not group_by and not groups:
        groups[()] = []                      # aggregate over empty input still yields one row

    out = []
    for key, rows in groups.items():
        vals = [_agg_value(s.func, [r[c] for r in rows] if c is not None else [], len(rows), c is None)
                for s, c in zip(specs, cols)]
        out.append(key + tuple(vals))
    return Relation(group_by + [s.output_name() for s in specs], out)