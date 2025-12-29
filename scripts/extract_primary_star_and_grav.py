from __future__ import annotations

import argparse
import csv
from collections import Counter
from typing import Any, Dict, Hashable, Optional, Tuple

from edsm_stream import iter_json_array_objects_gz


def as_float(x: Any) -> Optional[float]:
    try:
        return float(x)
    except Exception:
        return None


def as_int(x: Any) -> Optional[int]:
    if x is None:
        return None
    s = str(x).strip()
    if not s:
        return None
    try:
        return int(s)
    except Exception:
        try:
            return int(float(s))
        except Exception:
            return None


def norm(s: Any) -> str:
    return ("" if s is None else str(s)).strip()


def system_key(rec: Dict[str, Any]) -> Tuple[str, Hashable]:
    """
    Prefer stable numeric IDs for joins:
      1) systemId
      2) systemId64
      3) systemName
    Returns ("id"/"id64"/"name", value)
    """
    sid = as_int(rec.get("systemId"))
    if sid is not None:
        return ("id", sid)

    sid64 = as_int(rec.get("systemId64"))
    if sid64 is not None:
        return ("id64", sid64)

    name = norm(rec.get("systemName"))
    if name:
        return ("name", name)

    return ("none", "")


def is_interesting_grav(subtype: str) -> bool:
    """
    Include:
      - Black Hole
      - Neutron Star
      - all White Dwarf variants (e.g. "White Dwarf (DA) Star")
    """
    st = norm(subtype)
    if not st:
        return False
    if st == "Black Hole":
        return True
    if st == "Neutron Star":
        return True
    if st.startswith("White Dwarf"):
        return True
    return False


def choose_primary(existing: Optional[Dict[str, Any]], rec: Dict[str, Any]) -> Dict[str, Any]:
    """
    Pick best candidate for 'primary star' for a system.
    Preference order:
      1) isMainStar == True (if present)
      2) smallest distanceToArrival (usually 0 for main star)
    """
    is_main = rec.get("isMainStar")
    is_main = bool(is_main) if is_main is not None else False

    d = as_float(rec.get("distanceToArrival"))
    if d is None:
        d = 1e30

    if existing is None:
        out = dict(rec)
        out["_is_main"] = is_main
        out["_d"] = d
        return out

    # main star beats non-main star
    if is_main and not existing.get("_is_main", False):
        out = dict(rec)
        out["_is_main"] = is_main
        out["_d"] = d
        return out

    # if same main-flag, choose smallest distance
    if is_main == existing.get("_is_main", False) and d < existing.get("_d", 1e30):
        out = dict(rec)
        out["_is_main"] = is_main
        out["_d"] = d
        return out

    return existing


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--path", required=True, help="bodies*.json.gz")
    ap.add_argument("--out_primary", required=True)
    ap.add_argument("--out_interest", required=True)
    ap.add_argument("--limit", type=int, default=0, help="0 = no limit")
    args = ap.parse_args()

    # key: ("id"/"id64"/"name", value) -> best primary star record
    primary_by_system: Dict[Tuple[str, Hashable], Dict[str, Any]] = {}
    interest_rows: list[dict[str, Any]] = []
    subtype_counts = Counter()

    scanned = 0
    stars_seen = 0

    for rec in iter_json_array_objects_gz(args.path):
        scanned += 1
        if args.limit and scanned > args.limit:
            break

        if rec.get("type") != "Star":
            continue
        stars_seen += 1

        key_type, key_val = system_key(rec)
        if key_type == "none":
            continue

        sub = norm(rec.get("subType"))
        if sub:
            subtype_counts[sub] += 1

        k = (key_type, key_val)
        primary_by_system[k] = choose_primary(primary_by_system.get(k), rec)

        if is_interesting_grav(sub):
            interest_rows.append(
                {
                    "systemName": norm(rec.get("systemName")),
                    "systemId": as_int(rec.get("systemId")),
                    "systemId64": as_int(rec.get("systemId64")),
                    "bodyName": norm(rec.get("name")),
                    "subType": sub,
                    "distanceToArrival": rec.get("distanceToArrival"),
                    "id64": as_int(rec.get("id64")),
                    "updateTime": rec.get("updateTime"),
                }
            )

    # Write primary stars (deterministic order)
    primary_items = list(primary_by_system.items())
    primary_items.sort(key=lambda kv: (kv[0][0], str(kv[0][1])))

    with open(args.out_primary, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "systemName",
                "systemId",
                "systemId64",
                "primaryStarName",
                "primaryStarSubType",
                "distanceToArrival",
                "id64",
                "updateTime",
            ],
        )
        w.writeheader()
        for (_kt, _kv), rec in primary_items:
            w.writerow(
                {
                    "systemName": norm(rec.get("systemName")),
                    "systemId": as_int(rec.get("systemId")),
                    "systemId64": as_int(rec.get("systemId64")),
                    "primaryStarName": norm(rec.get("name")),
                    "primaryStarSubType": norm(rec.get("subType")),
                    "distanceToArrival": rec.get("distanceToArrival"),
                    "id64": as_int(rec.get("id64")),
                    "updateTime": rec.get("updateTime"),
                }
            )

    # Write interest bodies
    with open(args.out_interest, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "systemName",
                "systemId",
                "systemId64",
                "bodyName",
                "subType",
                "distanceToArrival",
                "id64",
                "updateTime",
            ],
        )
        w.writeheader()
        w.writerows(interest_rows)

    print(f"Scanned records: {scanned}")
    print(f"Star records seen: {stars_seen}")
    print(f"Systems with a primary-star pick: {len(primary_by_system)}")
    print(f"Interesting grav bodies (BH/NS/WD): {len(interest_rows)}")
    print("\nTop star subTypes:")
    for sub, c in subtype_counts.most_common(25):
        print(f"{c:>8}  {sub}")


if __name__ == "__main__":
    main()
