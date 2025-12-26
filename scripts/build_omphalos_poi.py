"""Build omphalos_poi.csv from EDastro 'Points of Interest' CSV.

We look for one of:
  - data/raw/edastro/points_of_interest.csv
  - data/raw/edastro/edsmPOI.csv

And normalize it into a compact schema:

    system_name,poi_name,poi_type,source
"""

import csv
import sys
from pathlib import Path
from typing import Dict, Iterable

# Import config
sys.path.append(str(Path(__file__).resolve().parents[1]))
from config import EDASTRO_RAW_DIR, POI_CSV  # type: ignore
from data_io import ensure_parent  # type: ignore


def pick_poi_source() -> Path:
    candidates = [
        EDASTRO_RAW_DIR / "points_of_interest.csv",
        EDASTRO_RAW_DIR / "edsmPOI.csv",
    ]
    for p in candidates:
        if p.exists():
            return p
    raise FileNotFoundError(f"No EDastro POI CSV found in {EDASTRO_RAW_DIR}")


def detect_columns(header: Iterable[str]) -> Dict[str, str]:
    """Heuristically detect system/name/type/source columns."""
    cols = list(header)
    lowered = {c.lower(): c for c in cols}

    def find(possible):
        for p in possible:
            for c in cols:
                if c.lower() == p:
                    return c
        return None

    system_col = find(["system", "system name", "star system", "system_name"])
    name_col = find(["name", "poi", "poi name", "label", "description"])
    type_col = find(["type", "category", "poi type"])
    source_col = find(["source", "src", "origin"])

    return {
        "system": system_col,
        "name": name_col,
        "type": type_col,
        "source": source_col,
    }


def build_omphalos_poi() -> None:
    src_path = pick_poi_source()
    ensure_parent(POI_CSV)

    print(f"[INFO] Reading POIs from {src_path}")

    with src_path.open("r", encoding="utf-8-sig", newline="") as f_in:
        reader = csv.DictReader(f_in)
        colmap = detect_columns(reader.fieldnames or [])
        if not colmap["system"] or not colmap["name"]:
            raise RuntimeError(
                f"Could not detect system/name columns in {src_path}; "
                f"got {reader.fieldnames}"
            )

        out_fields = ["system_name", "poi_name", "poi_type", "source"]
        rows_out = []

        for row in reader:
            sys_name = (row.get(colmap["system"]) or "").strip()
            poi_name = (row.get(colmap["name"]) or "").strip()
            if not sys_name or not poi_name:
                continue

            poi_type = ""
            if colmap["type"]:
                poi_type = (row.get(colmap["type"]) or "").strip()

            src = ""
            if colmap["source"]:
                src = (row.get(colmap["source"]) or "").strip()

            rows_out.append(
                {
                    "system_name": sys_name,
                    "poi_name": poi_name,
                    "poi_type": poi_type,
                    "source": src,
                }
            )

    with POI_CSV.open("w", encoding="utf-8", newline="") as f_out:
        writer = csv.DictWriter(f_out, fieldnames=out_fields)
        writer.writeheader()
        for r in rows_out:
            writer.writerow(r)

    print(f"[DONE] Wrote {len(rows_out):,} POIs -> {POI_CSV}")


if __name__ == "__main__":
    build_omphalos_poi()
