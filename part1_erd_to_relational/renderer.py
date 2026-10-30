from __future__ import annotations

import html
import re

import graphviz

from models import Table

HEADER_BG = "#2b5797"
PK_BG = "#fff2cc"


def _id(s: str) -> str:
    return re.sub(r"\W", "_", s)


def _label(table: Table) -> str:
    esc = html.escape
    rows = [
        f'<TR><TD COLSPAN="2" BGCOLOR="{HEADER_BG}">'
        f'<FONT COLOR="white"><B>{esc(table.name)}</B></FONT></TD></TR>'
    ]
    for c in table.columns:
        name = esc(c.name)
        if c.is_pk:
            name = f"<U>{name}</U>"
        tag = ", ".join(t for t, on in (("PK", c.is_pk), ("FK", c.is_fk)) if on)
        # Graphviz rejects an empty <FONT></FONT>, so use a non-breaking space instead
        tag_html = (f'<FONT POINT-SIZE="9" COLOR="#555555">{tag}</FONT>'
                    if tag else "&nbsp;")
        bg = f' BGCOLOR="{PK_BG}"' if c.is_pk else ""
        rows.append(
            f'<TR><TD PORT="{_id(c.name)}" ALIGN="LEFT"{bg}>{name}</TD>'
            f'<TD PORT="{_id(c.name)}_r">{tag_html}</TD></TR>'
        )
    return ('<<TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0" CELLPADDING="5">'
            + "".join(rows) + "</TABLE>>")


def build_graph(tables: list[Table]) -> graphviz.Digraph:
    dot = graphviz.Digraph("relational_schema")
    dot.attr(rankdir="LR", nodesep="0.6", ranksep="1.2", fontname="Helvetica")
    dot.attr("node", shape="plaintext", fontname="Helvetica")
    dot.attr("edge", color="#444444", arrowhead="normal")

    for t in tables:
        dot.node(_id(t.name), label=_label(t))

    for t in tables:
        for fk in t.foreign_keys:
            for col, ref_col in zip(fk.columns, fk.ref_columns):
                dot.edge(f"{_id(t.name)}:{_id(col)}_r", f"{_id(fk.ref_table)}:{_id(ref_col)}")
    return dot


def render_schema(tables: list[Table], out_dir: str, stem: str,
                  formats: tuple[str, ...] = ("png", "svg")) -> list[str]:
    dot = build_graph(tables)
    return [dot.render(filename=stem, directory=out_dir, format=fmt, cleanup=True)
            for fmt in formats]