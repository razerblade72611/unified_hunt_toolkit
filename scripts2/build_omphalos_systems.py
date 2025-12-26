# scripts/build_omphalos_systems.py

import csv
import gzip
import math
import sys
from pathlib import Path
from typing import Dict, Iterable, Set

import ijson

# Import config
sys.path.append(str(Path(__file__).resolve().parents[1]))
from config import (
    EDSM_RAW_DIR,
    EDASTRO_RAW_DIR,
    PROCESSED_DIR,
    MAX_RADIUS_LY,
    ALWAYS_KEEP_SYSTEMS,
)

# -------- Utility functions --------

def distance_to_sol(x: float, y: float, z: float) -> float:
    return math.sqrt(x * x + y * y + z * z)


def load_interesting_system_names() -> Set[str]:
    """
    Build a set of system names that are 'interesting' from EDastro:
    - Points of Interest (combined sources)
    - Nebulae Coordinates
    - Catalog Systems (named catalog entries)
    """
    names: Set[str] = set()

    poi_file = EDASTRO_RAW_DIR / "points_of_interest.csv"
    nebula_file = EDASTRO_RAW_DIR / "nebulae_coordinates.csv"
    catalog_file = EDASTRO_RAW_DIR / "catalog_systems.csv"

    def safe_read_csv(path: Path) -> Iterable[Dict[str, str]]:
        if not path.exists():
            print(f"[WARN] EDastro file missing: {path}")
            return []
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            return list(reader)

    # Points of Interest (combined POI sources) :contentReference[oaicite:6]{index=6}
    for row in safe_read_csv(poi_file):
        # EDastro POI CSV has a 'System' column
        sys_name = (row.get("System") or "").strip()
        if sys_name:
            names.add(sys_name)

    # Nebulae Coordinates :contentReference[oaicite:7]{index=7}
    for row in safe_read_csv(nebula_file):
        # Usually column 'System' or 'Name'
        sys_name = (row.get("System") or row.get("Name") or "").strip()
        if sys_name:
            names.add(sys_name)

    # Catalog Systems (non-procedural names) :contentReference[oaicite:8]{index=8}
    for row in safe_read_csv(catalog_file):
        # Typically 'System' or 'Name' again
        sys_name = (row.get("System") or row.get("Name") or "").strip()
        if sys_name:
            names.add(sys_name)

    print(f"[INFO] Loaded {len(names):,} interesting system names from EDastro.")
    return names


def iter_edsm_systems(edsm_path: Path):
    """
    Stream EDSM systemsWithCoordinates.json.gz using ijson.

    EDSM nightly dump structure is a top-level JSON array of systems.:contentReference[oaicite:9]{index=9}
    Each system typically has: name, coords {x, y, z}, requirePermit, permitName,
    information {allegiance, government, population,...}, primaryStar {...}.
    """
    if not edsm_path.exists():
        raise FileNotFoundError(f"EDSM dump not found: {edsm_path}")
    print(f"[INFO] Streaming systems from {edsm_path}")

    with gzip.open(edsm_path, "rb") as f:
        # "item" iterates each array element at root
        for system in ijson.items(f, "item"):
            yield system


def normalize_system_row(
    system: Dict,
    interesting_names: Set[str],
) -> Dict[str, str]:
    """
    Take one EDSM system object and flatten it into an Omphalos-ready row.
    """
    name = system.get("name") or ""
    name = str(name).strip()

    coords = system.get("coords") or {}
    x = coords.get("x")
    y = coords.get("y")
    z = coords.get("z")

    # Some systems may not have coords; skip those
    if x is None or y is None or z is None:
        return {}

    x = float(x)
    y = float(y)
    z = float(z)
    dist = distance_to_sol(x, y, z)

    require_permit = system.get("requirePermit", False)
    permit_name = system.get("permitName")

    information = system.get("information") or {}
    allegiance = information.get("allegiance")
    government = information.get("government")
    population = information.get("population")
    security = information.get("security")
    economy = information.get("economy")

    primary_star = system.get("primaryStar") or {}
    star_type = primary_star.get("type")
    star_name = primary_star.get("name")
    is_scoopable = primary_star.get("isScoopable")

    # Region will be derived later, but we include columns now.
    # You can later add a function that joins EDastro's regionID map.:contentReference[oaicite:10]{index=10}
    region_id = ""
    region_name = ""

    # Category & tags are your semantic overlay; we leave them blank for now.
    category = ""
    tags = ""

    is_interesting = name in interesting_names or name in ALWAYS_KEEP_SYSTEMS
    within_radius = dist <= MAX_RADIUS_LY

    keep = is_interesting or within_radius or name in ALWAYS_KEEP_SYSTEMS

    if not keep:
        return {}

    row = {
        "name": name,
        "x": f"{x:.6f}",
        "y": f"{y:.6f}",
        "z": f"{z:.6f}",
        "distance_to_sol": f"{dist:.3f}",
        "require_permit": str(bool(require_permit)),
        "permit_name": permit_name or "",
        "allegiance": allegiance or "",
        "government": government or "",
        "population": str(population) if population is not None else "",
        "security": security or "",
        "economy": economy or "",
        "primary_star_type": star_type or "",
        "primary_star_name": star_name or "",
        "primary_star_is_scoopable": (
            "" if is_scoopable is None else str(bool(is_scoopable))
        ),
        "region_id": region_id,
        "region_name": region_name,
        "category": category,
        "tags": tags,
        "source_flags": "edsm",
    }
    return row


def build_omphalos_systems():
    """
    Main pipeline:
    - Load interesting names from EDastro
    - Stream EDSM nightly dump
    - Keep systems within radius or with interesting names
    - Write omphalos_systems.csv
    """
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    out_path = PROCESSED_DIR / "omphalos_systems.csv"

    interesting_names = load_interesting_system_names()
    edsm_path = EDSM_RAW_DIR / "systemsWithCoordinates.json.gz"

    total_kept = 0

    fieldnames = [
        "name",
        "x",
        "y",
        "z",
        "distance_to_sol",
        "require_permit",
        "permit_name",
        "allegiance",
        "government",
        "population",
        "security",
        "economy",
        "primary_star_type",
        "primary_star_name",
        "primary_star_is_scoopable",
        "region_id",
        "region_name",
        "category",
        "tags",
        "source_flags",
    ]

    print(f"[INFO] Writing {out_path}")
    with out_path.open("w", encoding="utf-8", newline="") as f_out:
        writer = csv.DictWriter(f_out, fieldnames=fieldnames)
        writer.writeheader()

        for idx, system in enumerate(iter_edsm_systems(edsm_path), start=1):
            row = normalize_system_row(system, interesting_names)
            if row:
                writer.writerow(row)
                total_kept += 1

            if idx % 100000 == 0:
                print(f"[INFO] Processed {idx:,} systems, kept {total_kept:,}...")

    print(f"[DONE] Kept {total_kept:,} systems -> {out_path}")


if __name__ == "__main__":
    build_omphalos_systems()
