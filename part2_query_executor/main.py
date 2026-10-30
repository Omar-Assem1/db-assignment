from __future__ import annotations

import argparse
import json
import sys

from errors import QueryError
from executor import Executor
from operators import Relation
from printer import format_relation


def load_tables(path: str) -> dict[str, Relation]:
    """Accepts {"T": {"columns": [...], "rows": [[...]]}} or {"T": [{col: val}, ...]},
    optionally wrapped in a top-level "tables" key."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict) and isinstance(data.get("tables"), dict):
        data = data["tables"]
    if not isinstance(data, dict) or not data:
        raise ValueError("Dataset must be a JSON object mapping table names to tables")

    tables = {}
    for name, t in data.items():
        if isinstance(t, list):                              # list of row objects
            cols = list(t[0].keys()) if t else []
            rows = [tuple(r.get(c) for c in cols) for r in t]
        elif isinstance(t, dict) and "columns" in t and "rows" in t:
            cols, rows = t["columns"], t["rows"]
            for r in rows:
                if len(r) != len(cols):
                    raise ValueError(f"Table '{name}': row {r} does not match columns {cols}")
        else:
            raise ValueError(f"Table '{name}' must be a list of objects or have 'columns' and 'rows'")
        tables[name] = Relation(cols, [tuple(r) for r in rows])
    return tables


def run_query(ex: Executor, text: str) -> None:
    try:
        print(format_relation(ex.run_text(text)))
    except QueryError as e:
        print(f"Query error: {e}", file=sys.stderr)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Relational algebra query executor (no pandas).")
    p.add_argument("data", help="JSON file with the tables")
    p.add_argument("-q", "--query", action="append", help="query to run (repeatable)")
    p.add_argument("-f", "--file", help="file with one query per line ('--' starts a comment)")
    p.add_argument("--show-tables", action="store_true", help="print all input tables first")
    args = p.parse_args(argv)

    try:
        tables = load_tables(args.data)
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    ex = Executor(tables)

    if args.show_tables:
        for name, rel in tables.items():
            print(f"{name}:\n{format_relation(rel)}\n")

    queries = list(args.query or [])
    if args.file:
        with open(args.file, encoding="utf-8") as f:
            queries += [l.split("--")[0].strip() for l in f if l.split("--")[0].strip()]

    if queries:
        for q in queries:
            print(f"> {q}")
            run_query(ex, q)
            print()
        return 0

    print("Enter a query (empty line or Ctrl-D to quit).")
    try:
        while (line := input("ra> ").strip()):
            run_query(ex, line)
    except EOFError:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())