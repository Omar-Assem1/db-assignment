import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
for sub in ("part1_erd_to_relational", "part2_query_executor"):
    sys.path.insert(0, str(ROOT / sub))