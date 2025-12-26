"""Build omphalos_systems.csv from the EDSM systemsWithCoordinates dump.

This script deliberately keeps the schema simple and robust:

    name,x,y,z,distance_to_sol,allegiance,government,population

It streams the EDSM JSON via ijson so it can handle the multi-GB dump.
"""

import csv
import gzip
import math
import sys
from pathlib import Path
from typing import Dict, Iterable

import ijson  # pip install ijson

# Import config
sys.path.append(str(Path(__file__).resolve().parents[1]))
from config import EDSM_RAW_DIR, PROCESSED_DIR, SYSTEMS_CSV  # type: ignore
from data_io import ensure_parent  # type: ignore


def iter_edsm_systems(path: Path) -> Iterable[Dict]:
    """Stream systems from systemsWithCoordinates.json.gz using ijson."""
    with gzip.open(path, "rb") as f:
        for system in ijson.items(f, "item"):
            yield system


def normalize_row(system: Dict) -> Dict | None:
    name = (system.get("name") or "").strip()
    if not name:
        return None

    coords = system.get("coords") or {}
    try:
        x = float(coords.get("x"))
        y = float(coords.get("y"))
        z = float(coords.get("z"))
    except (TypeError, ValueError):
        return None

    info = system.get("information") or {}
    allegiance = (info.get("allegiance") or "").strip()
    government = (info.get("government") or "").strip()
    population = info.get("population") or ""

    # distance_to_sol = distance from (0,0,0)
    dist = math.sqrt(x * x + y * y + z * z)

    return {
        "name": name,
        "x": x,
        "y": y,
        "z": z,
        "distance_to_sol": f"{dist:.3f}",
        "allegiance": allegiance,
        "government": government,
        "population": str(population),
    }


def build_omphalos_systems() -> None:
    edsm_path = EDSM_RAW_DIR / "systemsWithCoordinates.json.gz"
    if not edsm_path.exists():
        raise FileNotFoundError(f"Missing EDSM dump at {edsm_path}")

    out_path = SYSTEMS_CSV
    ensure_parent(out_path)

    fieldnames = [
        "name",
        "x",
        "y",
        "z",
        "distance_to_sol",
        "allegiance",
        "government",
        "population",
    ]

    total = 0
    kept = 0

    print(f"[INFO] Streaming EDSM systems from {edsm_path}")
    with out_path.open("w", encoding="utf-8", newline="") as f_out:
        writer = csv.DictWriter(f_out, fieldnames=fieldnames)
        writer.writeheader()

        for total, system in enumerate(iter_edsm_systems(edsm_path), start=1):
            row = normalize_row(system)
            if row is not None:
                writer.writerow(row)
                kept += 1

            if total % 100_000 == 0:
                print(f"[INFO] Processed {total:,} systems, kept {kept:,} rows...")

    print(f"[DONE] Wrote {kept:,} systems -> {out_path}")


if __name__ == "__main__":
    build_omphalos_systems()
