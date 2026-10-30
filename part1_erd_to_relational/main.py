from __future__ import annotations

import argparse
import sys
from pathlib import Path

import graphviz

from erd_loader import load_erd
from renderer import render_schema
from transformer import transform


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Convert an ERD (JSON) to a relational schema diagram.")
    p.add_argument("erd", help="path to the ERD JSON file")
    p.add_argument("-o", "--out-dir", default="output", help="output directory (default: output)")
    p.add_argument("-n", "--name", help="output file name without extension (default: input file name)")
    p.add_argument("--no-render", action="store_true", help="only print the schema as text")
    args = p.parse_args(argv)

    try:
        entities, relationships = load_erd(args.erd)
        tables = transform(entities, relationships)
    except (ValueError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print("Relational schema:\n")
    print("\n\n".join(t.to_text() for t in tables))

    if args.no_render:
        return 0

    stem = args.name or Path(args.erd).stem
    try:
        files = render_schema(tables, args.out_dir, stem)
    except graphviz.ExecutableNotFound:
        print("\nError: Graphviz binary not found. Install it and make sure `dot` is on PATH.",
              file=sys.stderr)
        return 2

    print("\nGenerated:")
    for f in files:
        print(f"  {f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())