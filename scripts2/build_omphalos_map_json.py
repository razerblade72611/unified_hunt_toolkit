# scripts/build_omphalos_map_json.py

import csv
import json
import sys
from pathlib import Path
from collections import defaultdict

# make sure we can import config
ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from config import PROCESSED_DIR  # type: ignore

SYSTEMS_CSV = PROCESSED_DIR / "omphalos_systems.csv"
POI_CSV = PROCESSED_DIR / "omphalos_poi.csv"
OUT_JSON = PROCESSED_DIR / "omphalos_map.json"


def load_poi_index():
    """Return dict: system_name -> list of POIs."""
    poi_by_system = defaultdict(list)
    if not POI_CSV.exists():
        print(f"[WARN] No POI CSV found at {POI_CSV}")
        return poi_by_system

    with POI_CSV.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            sys_name = (row.get("system_name") or "").strip()
            if not sys_name:
                continue
            poi_by_system[sys_name].append(
                {
                    "name": (row.get("poi_name") or "").strip(),
                    "type": (row.get("poi_type") or "").strip(),
                    "source": (row.get("source") or "").strip(),
                }
            )
    print(f"[INFO] Loaded POIs for {len(poi_by_system):,} systems")
    return poi_by_system


def is_permit_locked(row):
    """Heuristic: treat multiple truthy forms as permit-locked."""
    rp = row.get("require_permit")
    pn = row.get("permit_name")

    if rp is True:
        return True

    if isinstance(rp, str):
        rps = rp.strip().lower()
        if rps in {"true", "1", "yes"}:
            return True

    if pn and pn.strip():
        return True

    return False


def has_tags_or_category(row):
    """Return True if either tags or category look non-empty."""
    tags = (row.get("tags") or "").strip()
    cat = (row.get("category") or "").strip()
    combined = f"{tags} {cat}".strip()
    if not combined:
        return False
    if combined == "[]":
        return False
    return True


def build_map_json(max_background=100_000):
    """
    Build omphalos_map.json with:
    - ALL 'interesting' systems (permit-locked, tagged, POI)
    - PLUS up to `max_background` generic background systems.
    This guarantees permit/tagged layers are populated even if rare.
    """
    if not SYSTEMS_CSV.exists():
        raise FileNotFoundError(f"Missing omphalos_systems.csv at {SYSTEMS_CSV}")

    poi_by_system = load_poi_index()

    interesting_systems = []
    background_systems = []

    with SYSTEMS_CSV.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = (row.get("name") or "").strip()
            if not name:
                continue

            # coords
            try:
                x = float(row["x"])
                y = float(row["y"])
                z = float(row["z"])
            except (KeyError, ValueError):
                continue

            # distance to Sol
            dist_str = (row.get("distance_to_sol") or "").strip()
            dist_val: float | str | None
            if dist_str == "":
                dist_val = 0.0
            else:
                try:
                    dist_val = float(dist_str)
                except ValueError:
                    dist_val = dist_str  # leave as string if it's weird

            poi_list = poi_by_system.get(name, [])
            poi_count = len(poi_list)

            base_record = {
                "name": name,
                "x": x,
                "y": y,
                "z": z,
                "distance_to_sol": dist_val,
                "require_permit": row.get("require_permit"),
                "permit_name": row.get("permit_name") or "",
                "allegiance": row.get("allegiance") or "",
                "government": row.get("government") or "",
                "population": row.get("population") or "",
                "primary_star_type": row.get("primary_star_type") or "",
                "region_name": row.get("region_name") or "",
                "category": row.get("category") or "",
                "tags": row.get("tags") or "",
                "poi_count": poi_count,
            }

            # Decide if this system is 'interesting'
            permit = is_permit_locked(row)
            tagged = has_tags_or_category(row)
            has_poi = poi_count > 0

            if permit or tagged or has_poi:
                interesting_systems.append(base_record)
            else:
                if len(background_systems) < max_background:
                    background_systems.append(base_record)

    systems_out = interesting_systems + background_systems

    print(
        f"[INFO] Interesting systems: {len(interesting_systems):,} "
        f"(permit/tagged/POI); background sampled: {len(background_systems):,}"
    )
    print(f"[INFO] Total systems written: {len(systems_out):,}")

    data = {
        "systems": systems_out,
        "poi": [
            {"system": sys_name, **poi}
            for sys_name, poi_list in poi_by_system.items()
            for poi in poi_list
        ],
    }

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    with OUT_JSON.open("w", encoding="utf-8") as f_out:
        json.dump(data, f_out, indent=2)

    print(
        f"[DONE] Wrote {len(systems_out):,} systems and "
        f"{len(data['poi']):,} POIs to {OUT_JSON}"
    )


if __name__ == "__main__":
    # Adjust max_background if you want more/fewer generic systems
    build_map_json(max_background=100_000)
