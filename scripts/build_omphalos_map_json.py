"""Build Omphalos JSON files for the viewer: base map + overlays.

Outputs under data/processed/:

  - omphalos_map_base.json
  - overlay_poi.json
  - overlay_permits.json
  - overlay_lore_hubs.json

Required inputs:

  - data/processed/omphalos_systems.csv      (from build_omphalos_systems.py)
  - data/processed/omphalos_poi.csv          (from build_omphalos_poi.py)
  - data/raw/community/permit_locked_systems.csv
  - data/raw/community/lore_hubs.csv         (you maintain this by hand)

The viewer can then load each of these JSON files as independent layers.
"""

import csv
import sys
from pathlib import Path
from typing import Dict, List, Any

# Import config
sys.path.append(str(Path(__file__).resolve().parents[1]))
from config import (  # type: ignore
    SYSTEMS_CSV,
    POI_CSV,
    PERMIT_CSV,
    LORE_HUBS_CSV,
    MAP_BASE_JSON,
    OVERLAY_POI_JSON,
    OVERLAY_PERMITS_JSON,
    OVERLAY_LORE_HUBS_JSON,
)
from data_io import ensure_parent, write_json  # type: ignore


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_systems() -> List[Dict[str, Any]]:
    """Load all systems from omphalos_systems.csv into a list.

    We keep the schema minimal and let overlays provide extra semantics.
    """
    systems: List[Dict[str, Any]] = []
    with SYSTEMS_CSV.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                x = float(row.get("x", "0") or 0.0)
                y = float(row.get("y", "0") or 0.0)
                z = float(row.get("z", "0") or 0.0)
            except ValueError:
                continue

            dist_str = (row.get("distance_to_sol") or "").strip()
            try:
                dist = float(dist_str) if dist_str else 0.0
            except ValueError:
                dist = 0.0

            systems.append(
                {
                    "name": (row.get("name") or "").strip(),
                    "x": x,
                    "y": y,
                    "z": z,
                    "distance_to_sol": dist,
                    "allegiance": (row.get("allegiance") or "").strip(),
                    "government": (row.get("government") or "").strip(),
                    "population": (row.get("population") or "").strip(),
                }
            )
    return systems


def build_system_index(systems: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    return {s["name"]: s for s in systems if s.get("name")}


# ---------------------------------------------------------------------------
# Base map JSON
# ---------------------------------------------------------------------------

def build_base_json(systems: List[Dict[str, Any]], max_background: int = 100_000) -> None:
    """Downsample systems into a base map JSON.

    This keeps the galaxy recognizable without overloading the browser.
    """
    ensure_parent(MAP_BASE_JSON)

    if len(systems) <= max_background:
        sample = systems
    else:
        # Simple stride sampling for reproducibility
        stride = max(1, len(systems) // max_background)
        sample = systems[::stride]

    write_json(
        MAP_BASE_JSON,
        {
            "systems": sample,
            "meta": {
                "total_systems": len(systems),
                "sample_size": len(sample),
            },
        },
    )
    print(f"[DONE] Wrote base map with {len(sample):,} systems -> {MAP_BASE_JSON}")


# ---------------------------------------------------------------------------
# POI overlay
# ---------------------------------------------------------------------------

def build_poi_overlay(sys_index: Dict[str, Dict[str, Any]]) -> None:
    if not POI_CSV.exists():
        print(f"[WARN] No POI CSV at {POI_CSV}; overlay_poi.json will be empty.")
        write_json(OVERLAY_POI_JSON, {"points": []})
        return

    points = []
    with POI_CSV.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            sys_name = (row.get("system_name") or "").strip()
            poi_name = (row.get("poi_name") or "").strip()
            if not sys_name or not poi_name:
                continue

            sys_rec = sys_index.get(sys_name)
            if not sys_rec:
                # Skip POIs whose system is not in our systems CSV
                continue

            points.append(
                {
                    "system": sys_name,
                    "x": sys_rec["x"],
                    "y": sys_rec["y"],
                    "z": sys_rec["z"],
                    "poi_name": poi_name,
                    "poi_type": (row.get("poi_type") or "").strip(),
                    "source": (row.get("source") or "").strip(),
                }
            )

    write_json(OVERLAY_POI_JSON, {"points": points})
    print(f"[DONE] Wrote POI overlay with {len(points):,} points -> {OVERLAY_POI_JSON}")


# ---------------------------------------------------------------------------
# Permit overlay
# ---------------------------------------------------------------------------

def build_permit_overlay(sys_index: Dict[str, Dict[str, Any]]) -> None:
    if not PERMIT_CSV.exists():
        print(f"[WARN] No permit CSV at {PERMIT_CSV}; overlay_permits.json will be empty.")
        write_json(OVERLAY_PERMITS_JSON, {"systems": []})
        return

    systems_out = []
    missing = 0

    with PERMIT_CSV.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            loc = (row.get("Location") or "").strip()
            if not loc:
                continue

            sys_rec = sys_index.get(loc)
            if not sys_rec:
                # Some rows are region or 'none' etc; we only include ones
                # that match an actual system in our index.
                missing += 1
                continue

            systems_out.append(
                {
                    "system_name": loc,
                    "x": sys_rec["x"],
                    "y": sys_rec["y"],
                    "z": sys_rec["z"],
                    "permit_name": (row.get("Permit Name") or "").strip(),
                    "faction": (row.get("Faction") or "").strip(),
                    "requires": (row.get("Requires (Rank / Rep)") or "").strip(),
                    "benefits": (row.get("Benefits") or "").strip(),
                    "denial_message": (row.get("Denial Message") or "").strip(),
                    "permit_type": (row.get("Type") or "").strip(),
                    "note": (row.get("NOTE") or "").strip(),
                }
            )

    write_json(OVERLAY_PERMITS_JSON, {"systems": systems_out})
    print(
        f"[DONE] Wrote permit overlay with {len(systems_out):,} systems "
        f"(skipped {missing:,} non-system/unknown entries) -> {OVERLAY_PERMITS_JSON}"
    )


# ---------------------------------------------------------------------------
# Lore hubs overlay
# ---------------------------------------------------------------------------

def build_lore_hubs_overlay(sys_index: Dict[str, Dict[str, Any]]) -> None:
    """Build overlay_lore_hubs.json from lore_hubs.csv.

    Expected columns in lore_hubs.csv:

      name,category,tags,weight,notes

    - 'name' must match system name in omphalos_systems.csv
    - 'weight' is optional (float); default 1.0
    """
    if not LORE_HUBS_CSV.exists():
        print(f"[WARN] No lore hubs CSV at {LORE_HUBS_CSV}; overlay_lore_hubs.json will be empty.")
        write_json(OVERLAY_LORE_HUBS_JSON, {"systems": []})
        return

    systems_out = []
    missing = 0

    with LORE_HUBS_CSV.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = (row.get("name") or "").strip()
            if not name:
                continue
            sys_rec = sys_index.get(name)
            if not sys_rec:
                missing += 1
                continue

            weight_str = (row.get("weight") or "").strip()
            try:
                weight = float(weight_str) if weight_str else 1.0
            except ValueError:
                weight = 1.0

            systems_out.append(
                {
                    "name": name,
                    "x": sys_rec["x"],
                    "y": sys_rec["y"],
                    "z": sys_rec["z"],
                    "category": (row.get("category") or "").strip(),
                    "tags": (row.get("tags") or "").strip(),
                    "weight": weight,
                    "notes": (row.get("notes") or "").strip(),
                }
            )

    write_json(OVERLAY_LORE_HUBS_JSON, {"systems": systems_out})
    print(
        f"[DONE] Wrote lore hubs overlay with {len(systems_out):,} systems "
        f"(skipped {missing:,} names not in omphalos_systems.csv) -> {OVERLAY_LORE_HUBS_JSON}"
    )


# ---------------------------------------------------------------------------
# Main entrypoint
# ---------------------------------------------------------------------------

def main() -> None:
    systems = load_systems()
    print(f"[INFO] Loaded {len(systems):,} systems from {SYSTEMS_CSV}")
    sys_index = build_system_index(systems)

    build_base_json(systems)
    build_poi_overlay(sys_index)
    build_permit_overlay(sys_index)
    build_lore_hubs_overlay(sys_index)


if __name__ == "__main__":
    main()
