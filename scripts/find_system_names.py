from __future__ import annotations
import argparse, csv
from pathlib import Path

def header_map(header): return {h.strip().lower(): i for i, h in enumerate(header)}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default="data/processed/omphalos_systems.csv")
    ap.add_argument("--q", required=True, help="substring to find (case-insensitive)")
    ap.add_argument("--limit", type=int, default=50)
    args = ap.parse_args()

    q = args.q.lower()
    path = Path(args.csv)
    if not path.exists():
        raise SystemExit(f"Missing: {path}")

    with path.open("r", encoding="utf-8-sig", newline="") as f:
        r = csv.reader(f)
        header = next(r)
        hm = header_map(header)
        name_i = hm.get("name") or hm.get("system") or hm.get("system_name") or 0

        n = 0
        for row in r:
            if len(row) <= name_i: 
                continue
            name = row[name_i].strip()
            if q in name.lower():
                print(name)
                n += 1
                if n >= args.limit:
                    break

if __name__ == "__main__":
    main()
