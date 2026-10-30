from __future__ import annotations

from operators import Relation


def _fmt(v) -> str:
    if v is None:
        return "NULL"
    if isinstance(v, bool):
        return "TRUE" if v else "FALSE"
    if isinstance(v, float):
        return f"{v:.4f}".rstrip("0").rstrip(".")
    return str(v)


def format_relation(rel: Relation) -> str:
    cells = [[_fmt(v) for v in r] for r in rel.rows]
    widths = [max([len(c)] + [len(r[i]) for r in cells]) for i, c in enumerate(rel.columns)]
    sep = "+" + "+".join("-" * (w + 2) for w in widths) + "+"

    def line(vals, numeric=None):
        return "|" + "|".join(f" {v:<{w}} " for v, w in zip(vals, widths)) + "|"

    out = [sep, line(rel.columns), sep]
    out += [line(r) for r in cells]
    out += [sep, f"({len(rel.rows)} row{'s' if len(rel.rows) != 1 else ''})"]
    return "\n".join(out)