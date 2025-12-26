# scripts/build_omphalos_poi.py

import csv
import sys
from pathlib import Path
from typing import Dict, Iterable

# Import config
sys.path.append(str(Path(__file__).resolve().parents[1]))
from config import EDASTRO_RAW_DIR, PROCESSED_DIR

POI_IN = EDASTRO_RAW_DIR / "points_of_interest.csv"
NEBULA_IN = EDASTRO_RAW_DIR / "nebulae_coordinates.csv"
OUT_PATH = PROCESSED_DIR / "omphalos_poi.csv"


def read_csv(path: Path) -> Iterable[Dict[str, str]]:
    if not path.exists():
        print(f"[WARN] Missing CSV: {path}")
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def build_poi():
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    poi_rows = []
    # EDastro combined POIs :contentReference[oaicite:11]{index=11}
    for row in read_csv(POI_IN):
        poi_rows.append(
            {
                "system_name": (row.get("System") or "").strip(),
                "poi_name": (row.get("Name") or "").strip(),
                "poi_type": (row.get("Type") or "").strip(),
                "source": (row.get("Source") or "").strip(),
                "notes": (row.get("Notes") or "").strip(),
            }
        )

    # Nebulae coordinates (treat each nebula as a POI) :contentReference[oaicite:12]{index=12}
    for row in read_csv(NEBULA_IN):
        system_name = (row.get("System") or row.get("Name") or "").strip()
        neb_name = (row.get("Name") or "").strip()
        poi_rows.append(
            {
                "system_name": system_name,
                "poi_name": neb_name,
                "poi_type": "Nebula",
                "source": "EDAstro Nebulae",
                "notes": "",
            }
        )

    fieldnames = ["system_name", "poi_name", "poi_type", "source", "notes"]
    print(f"[INFO] Writing {len(poi_rows):,} POIs -> {OUT_PATH}")
    with OUT_PATH.open("w", encoding="utf-8", newline="") as f_out:
        writer = csv.DictWriter(f_out, fieldnames=fieldnames)
        writer.writeheader()
        for row in poi_rows:
            if row["system_name"]:
                writer.writerow(row)

    print("[DONE] omphalos_poi.csv built.")


if __name__ == "__main__":
    build_poi()
