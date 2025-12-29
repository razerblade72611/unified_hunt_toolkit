from __future__ import annotations

import argparse
import csv
import gzip
import json
from typing import Any, Dict, Iterator, Optional, Tuple


def norm_name(s: Any) -> str:
    return ("" if s is None else str(s)).strip()


def safe_int(x: Any) -> Optional[int]:
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


def iter_systems_with_coords_gz(path: str) -> Iterator[Dict[str, Any]]:
    """
    Stream a gzipped JSON array: [ {...}, {...}, ... ]
    Matches EDSM systemsWithCoordinates dumps.
    """
    with gzip.open(path, "rt", encoding="utf-8", errors="replace") as f:
        # consume whitespace to first token
        ch = f.read(1)
        while ch and ch.isspace():
            ch = f.read(1)
        if ch != "[":
            raise ValueError(f"Expected '[' at start, got {ch!r}")

        # scan to first '{' or ']'
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

                        # scan to next '{' or end ']'
                        c2 = f.read(1)
                        while c2 and c2 not in "{]":
                            c2 = f.read(1)
                        if not c2 or c2 == "]":
                            return

                        buf = ["{"]
                        depth = 1
                        in_str = False
                        esc = False


def load_primary_maps(primary_csv: str) -> Tuple[dict[int, dict], dict[int, dict], dict[str, dict]]:
    """
    Loads the primary-star CSV written by extract_primary_star_and_grav.py.

    Returns:
      by_id   (systemId -> row)
      by_id64 (systemId64 -> row)
      by_name (systemName -> row)
    """
    by_id: dict[int, dict] = {}
    by_id64: dict[int, dict] = {}
    by_name: dict[str, dict] = {}

    rows = 0
    with open(primary_csv, "r", encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        if not r.fieldnames:
            raise ValueError("Primary CSV missing header row")

        # We expect: systemName, systemId, systemId64, primaryStarName, primaryStarSubType, ...
        for row in r:
            rows += 1
            sid = safe_int(row.get("systemId"))
            sid64 = safe_int(row.get("systemId64"))
            nm = norm_name(row.get("systemName"))

            if sid is not None:
                by_id[sid] = row
            if sid64 is not None:
                by_id64[sid64] = row
            if nm:
                by_name[nm] = row

    print(f"Loaded primary rows: {rows}")
    print(f"Primary map keys: by_id={len(by_id)}  by_id64={len(by_id64)}  by_name={len(by_name)}")
    return by_id, by_id64, by_name


def first_nonempty(row: dict, *keys: str) -> str:
    for k in keys:
        v = row.get(k)
        if v is None:
            continue
        s = str(v).strip()
        if s:
            return s
    return ""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--systems_path", required=True, help="systemsWithCoordinates*.json.gz")
    ap.add_argument("--primary_csv", required=True, help="edsm_primary_star_*.csv")
    ap.add_argument("--out_csv", required=True)
    ap.add_argument(
        "--only_matched",
        action="store_true",
        help="Write ONLY systems that matched primary-star rows (recommended for 7days bodies joins).",
    )
    args = ap.parse_args()

    by_id, by_id64, by_name = load_primary_maps(args.primary_csv)

    matched = 0
    via_id = 0
    via_id64 = 0
    via_name = 0
    written = 0

    with open(args.out_csv, "w", encoding="utf-8", newline="") as out:
        fieldnames = [
            "name", "id", "id64", "date",
            "x", "y", "z",
            "primary_type", "primary_subType", "primary_star_name",
        ]
        w = csv.DictWriter(out, fieldnames=fieldnames)
        w.writeheader()

        for sysrec in iter_systems_with_coords_gz(args.systems_path):
            name = sysrec.get("name")
            sid = safe_int(sysrec.get("id"))
            sid64 = safe_int(sysrec.get("id64"))
            dt = sysrec.get("date")

            coords = sysrec.get("coords") or {}
            x = coords.get("x")
            y = coords.get("y")
            z = coords.get("z")

            prow = None
            if sid is not None and sid in by_id:
                prow = by_id[sid]
                via_id += 1
            elif sid64 is not None and sid64 in by_id64:
                prow = by_id64[sid64]
                via_id64 += 1
            else:
                nm = norm_name(name)
                if nm and nm in by_name:
                    prow = by_name[nm]
                    via_name += 1

            if not prow and args.only_matched:
                continue

            row_out = {
                "name": name,
                "id": sid,
                "id64": sid64,
                "date": dt,
                "x": x,
                "y": y,
                "z": z,
                "primary_type": "",
                "primary_subType": "",
                "primary_star_name": "",
            }

            if prow:
                matched += 1
                row_out["primary_star_name"] = first_nonempty(prow, "primaryStarName")
                row_out["primary_subType"] = first_nonempty(prow, "primaryStarSubType")
                # We don't export a primaryStarType; keep it as "Star" if subtype exists.
                if row_out["primary_subType"]:
                    row_out["primary_type"] = "Star"

            w.writerow(row_out)
            written += 1

    print(f"Wrote: {args.out_csv}")
    print(f"Systems written: {written}")
    print(f"Matched primary star info for: {matched}")
    print(f"  - via systemId:  {via_id}")
    print(f"  - via systemId64:{via_id64}")
    print(f"  - via name:      {via_name}")


if __name__ == "__main__":
    main()
