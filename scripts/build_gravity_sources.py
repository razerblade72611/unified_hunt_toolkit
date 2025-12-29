from __future__ import annotations

import argparse
import csv
import gzip
import json
from typing import Any, Dict, Iterator, List, Optional, Set, Tuple


# ---------------------------
# Streaming systemsWithCoordinates.json.gz
# ---------------------------
def iter_systems_with_coords_gz(path: str) -> Iterator[Dict[str, Any]]:
    """
    Stream a gzipped JSON array: [ {...}, {...}, ... ]
    Works for EDSM systemsWithCoordinates*.json.gz
    """
    with gzip.open(path, "rt", encoding="utf-8", errors="replace") as f:
        # Skip whitespace to first token
        ch = f.read(1)
        while ch and ch.isspace():
            ch = f.read(1)
        if ch != "[":
            raise ValueError(f"Expected JSON array '[' at start, got {ch!r}")

        # Move to first '{' or ']'
        c = f.read(1)
        while c and c not in "{]":
            c = f.read(1)
        if c == "]":
            return
        if c != "{":
            raise ValueError("Expected '{' after '['")

        buf = ["{"]
        depth = 1
        in_str = False
        esc = False

        while True:
            c = f.read(1)
            if not c:
                raise ValueError("EOF mid-object")

            buf.append(c)

            if in_str:
                if esc:
                    esc = False
                elif c == "\\":
                    esc = True
                elif c == '"':
                    in_str = False
            else:
                if c == '"':
                    in_str = True
                elif c == "{":
                    depth += 1
                elif c == "}":
                    depth -= 1
                    if depth == 0:
                        yield json.loads("".join(buf))
                        buf = []

                        # Seek next '{' or end ']'
                        c2 = f.read(1)
                        while c2 and c2 not in "{]":
                            c2 = f.read(1)
                        if not c2 or c2 == "]":
                            return

                        buf = ["{"]
                        depth = 1
                        in_str = False
                        esc = False


def as_int(x: Any) -> Optional[int]:
    if x is None:
        return None
    s = str(x).strip()
    if not s:
        return None
    try:
        return int(s)
    except ValueError:
        try:
            return int(float(s))
        except Exception:
            return None


def as_float(x: Any) -> Optional[float]:
    if x is None:
        return None
    s = str(x).strip()
    if not s:
        return None
    try:
        return float(s)
    except Exception:
        return None


def kind_and_weight(subtype: str) -> Tuple[str, float]:
    """
    Simple visual weights for warp rendering.
    You can tune these later; they’re intended for *visualization*, not physics.
    """
    st = (subtype or "").strip()

    if st == "Black Hole":
        return ("BH", 1.00)

    if st == "Neutron Star":
        return ("NS", 0.85)

    if st.startswith("White Dwarf"):
        # keep all WD variants visible but weaker than BH/NS
        return ("WD", 0.50)

    # fallback
    return ("OTHER", 0.35)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--interest_csv", required=True, help="edsm_interest_grav_*.csv")
    ap.add_argument("--systems_coords_gz", required=True, help="systemsWithCoordinates.json.gz (FULL dump recommended)")
    ap.add_argument("--out_json", required=True, help="data/processed/gravity_sources.json")
    ap.add_argument("--limit_systems", type=int, default=0, help="Debug: stop scanning systems after N (0=no limit)")
    args = ap.parse_args()

    # 1) Load interest CSV (6510 rows) and collect needed systemIds
    interest_rows: List[Dict[str, Any]] = []
    need_system_ids: Set[int] = set()

    with open(args.interest_csv, "r", encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            sid = as_int(row.get("systemId"))
            if sid is None:
                continue
            need_system_ids.add(sid)
            interest_rows.append(row)

    print(f"Interest rows loaded: {len(interest_rows)}")
    print(f"Unique systems needed: {len(need_system_ids)}")

    # 2) Stream systemsWithCoordinates and grab coords for only needed systems
    coords_by_system_id: Dict[int, Tuple[str, float, float, float, Optional[int]]] = {}

    scanned = 0
    matched = 0
    for sysrec in iter_systems_with_coords_gz(args.systems_coords_gz):
        scanned += 1
        if args.limit_systems and scanned > args.limit_systems:
            break

        sid = as_int(sysrec.get("id"))
        if sid is None or sid not in need_system_ids:
            continue

        name = sysrec.get("name") or ""
        coords = sysrec.get("coords") or {}
        x = as_float(coords.get("x"))
        y = as_float(coords.get("y"))
        z = as_float(coords.get("z"))
        sid64 = as_int(sysrec.get("id64"))

        if x is None or y is None or z is None:
            continue

        coords_by_system_id[sid] = (name, x, y, z, sid64)
        matched += 1

        if matched % 500 == 0:
            print(f"  matched coords: {matched} (scanned: {scanned})")

    print(f"Systems scanned: {scanned}")
    print(f"Systems coords matched: {len(coords_by_system_id)}")

    # 3) Emit gravity sources json using system coords (star location)
    sources = []
    missing_coords = 0

    for row in interest_rows:
        sid = as_int(row.get("systemId"))
        if sid is None:
            continue

        got = coords_by_system_id.get(sid)
        if not got:
            missing_coords += 1
            continue

        sys_name, x, y, z, sys_id64_from_coords = got

        subtype = (row.get("subType") or "").strip()
        kind, w = kind_and_weight(subtype)

        body_name = (row.get("bodyName") or "").strip()
        body_id64 = as_int(row.get("id64"))  # body id64

        # Stable unique id for selection UI
        # Prefer body id64; else fall back to systemId:bodyName
        uid = str(body_id64) if body_id64 is not None else f"{sid}:{body_name or kind}"

        sources.append({
            "id": uid,
            "kind": kind,
            "subType": subtype,
            "system": sys_name,
            "systemId": sid,
            "systemId64": as_int(row.get("systemId64")) or sys_id64_from_coords,
            "body_name": body_name,
            "body_id64": body_id64,
            "distanceToArrival": as_float(row.get("distanceToArrival")),
            "weight": w,
            "x": x,
            "y": y,
            "z": z,
        })

    out = {
        "meta": {
            "source_interest_csv": args.interest_csv,
            "source_systems_coords": args.systems_coords_gz,
            "sources": len(sources),
            "missing_coords": missing_coords,
            "note": "Coordinates are system (star) coords. distanceToArrival is retained for reference but not used for positioning.",
        },
        "sources": sources,
    }

    with open(args.out_json, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False)

    print(f"Wrote: {args.out_json}")
    print(f"Gravity sources: {len(sources)}")
    print(f"Interest rows missing coords: {missing_coords}")


if __name__ == "__main__":
    main()
