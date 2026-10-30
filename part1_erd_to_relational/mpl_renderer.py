from __future__ import annotations

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, Rectangle

from models import Table

HEADER_BG, PK_BG = "#2b5797", "#fff2cc"
FONT, TAG_FONT = 10, 7
ROW_H, PAD, COL_GAP, ROW_GAP, MARGIN = 26, 8, 130, 40, 30


def _layers(tables: list[Table]) -> dict[str, int]:
    """Column index per table: referenced tables go to the right of the tables pointing at them."""
    by = {t.name: t for t in tables}
    depth: dict[str, int] = {}

    def d(name: str, stack: tuple = ()) -> int:
        if name in depth:
            return depth[name]
        refs = [fk.ref_table for fk in by[name].foreign_keys
                if fk.ref_table != name and fk.ref_table not in stack]
        depth[name] = 0 if not refs else 1 + max(d(r, stack + (name,)) for r in refs)
        return depth[name]

    for t in tables:
        d(t.name)
    top = max(depth.values(), default=0)
    return {n: top - v for n, v in depth.items()}


def render_schema_mpl(tables: list[Table], out_dir: str, stem: str,
                      formats: tuple[str, ...] = ("png", "svg")) -> list[str]:
    from pathlib import Path

    fig = plt.figure(figsize=(8, 6), dpi=72)
    measure_ax = fig.add_axes([0, 0, 1, 1])
    rend = fig.canvas.get_renderer()

    def text_w(s: str, size: float, bold=False) -> float:
        t = measure_ax.text(0, 0, s, fontsize=size, fontweight="bold" if bold else "normal")
        w = t.get_window_extent(rend).width
        t.remove()
        return w

    # ---- sizes and positions (in points) ----
    info = {}
    for t in tables:
        name_w = max([text_w(c.name, FONT) for c in t.columns] + [text_w(t.name, FONT + 1, True) - 60])
        tag_w = max([text_w(", ".join(x for x, on in (("PK", c.is_pk), ("FK", c.is_fk)) if on), TAG_FONT)
                     for c in t.columns] + [0])
        info[t.name] = dict(w=max(name_w + tag_w + 4 * PAD, text_w(t.name, FONT + 1, True) + 2 * PAD),
                            h=ROW_H * (len(t.columns) + 1), name_w=name_w)

    layer = _layers(tables)
    cols: dict[int, list[Table]] = {}
    for t in tables:
        cols.setdefault(layer[t.name], []).append(t)

    x = MARGIN
    col_h = {}
    for li in sorted(cols):
        width = max(info[t.name]["w"] for t in cols[li])
        y = MARGIN
        for t in cols[li]:
            info[t.name].update(x=x, y=y)
            y += info[t.name]["h"] + ROW_GAP
        col_h[li] = y - ROW_GAP + MARGIN
        x += width + COL_GAP
    W, H = x - COL_GAP + MARGIN, max(col_h.values(), default=100)

    # centre shorter columns vertically
    for li, ts in cols.items():
        shift = (H - col_h[li]) / 2
        for t in ts:
            info[t.name]["y"] += shift

    fig.clf()
    fig.set_size_inches(W / 72, H / 72)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W); ax.set_ylim(H, 0); ax.axis("off")

    def row_y(tname: str, col: str) -> float:
        tb = next(t for t in tables if t.name == tname)
        i = [c.name for c in tb.columns].index(col)
        return info[tname]["y"] + ROW_H * (i + 1) + ROW_H / 2

    # ---- arrows first (boxes drawn over them) ----
    for t in tables:
        i = info[t.name]
        for fk in t.foreign_keys:
            r = info[fk.ref_table]
            for col, rcol in zip(fk.columns, fk.ref_columns):
                if fk.ref_table == t.name:       # self reference: loop on the right side
                    start, end, style = (i["x"] + i["w"], row_y(t.name, col)), \
                                        (i["x"] + i["w"], row_y(t.name, rcol)), "arc3,rad=-0.6"
                elif r["x"] > i["x"]:
                    start, end, style = (i["x"] + i["w"], row_y(t.name, col)), \
                                        (r["x"], row_y(fk.ref_table, rcol)), "arc3,rad=0"
                else:                            # target is not to the right: go around
                    start, end, style = (i["x"], row_y(t.name, col)), \
                                        (r["x"] + r["w"], row_y(fk.ref_table, rcol)), "arc3,rad=0"
                ax.add_patch(FancyArrowPatch(start, end, connectionstyle=style, arrowstyle="-|>",
                                             mutation_scale=12, color="#444444", lw=1.1, zorder=1))

    # ---- tables ----
    for t in tables:
        i = info[t.name]
        ax.add_patch(Rectangle((i["x"], i["y"]), i["w"], ROW_H, fc=HEADER_BG, ec="black", lw=1, zorder=2))
        ax.text(i["x"] + i["w"] / 2, i["y"] + ROW_H / 2, t.name, color="white", fontsize=FONT + 1,
                fontweight="bold", ha="center", va="center", zorder=3)
        for k, c in enumerate(t.columns):
            y0 = i["y"] + ROW_H * (k + 1)
            ax.add_patch(Rectangle((i["x"], y0), i["w"], ROW_H, fc=PK_BG if c.is_pk else "white",
                                   ec="black", lw=1, zorder=2))
            ty = y0 + ROW_H / 2
            ax.text(i["x"] + PAD, ty, c.name, fontsize=FONT, ha="left", va="center", zorder=3)
            if c.is_pk:                              # underline primary keys
                uw = text_w(c.name, FONT)
                ax.plot([i["x"] + PAD, i["x"] + PAD + uw], [ty + 7, ty + 7], color="black", lw=0.9, zorder=3)
            tag = ", ".join(x for x, on in (("PK", c.is_pk), ("FK", c.is_fk)) if on)
            if tag:
                ax.text(i["x"] + i["w"] - PAD, ty, tag, fontsize=TAG_FONT, color="#555555",
                        ha="right", va="center", zorder=3)

    out = []
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    for fmt in formats:
        p = str(Path(out_dir) / f"{stem}.{fmt}")
        fig.savefig(p, format=fmt, dpi=200 if fmt == "png" else 72)
        out.append(p)
    plt.close(fig)
    return out