from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]

DEFAULT_ANCHORS = ROOT / "data" / "sky_constellation_anchors.json"
DEFAULT_OUT = ROOT / "data" / "processed" / "sky_ed.json"

DEFAULT_CATALOGS = [
    ROOT / "data" / "processed" / "omphalos_systems.csv",
    ROOT / "data" / "guardian_systems.csv",
]


# ---------------------------
# CSV catalog lookup
# ---------------------------
def read_header_map(header: List[str]) -> Dict[str, int]:
    return {h.strip().lower(): i for i, h in enumerate(header)}


def find_col(hmap: Dict[str, int], candidates: List[str]) -> Optional[int]:
    for c in candidates:
        idx = hmap.get(c.lower())
        if idx is not None:
            return idx
    return None


def iter_csv_rows(path: Path) -> Iterable[List[str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        for row in reader:
            yield row


def load_coords_from_catalogs(
    target_names: List[str],
    catalogs: List[Path],
    strict_case: bool = False,
) -> Tuple[Dict[str, Tuple[float, float, float]], Dict[str, List[str]]]:
    """
    Scans catalogs sequentially and returns:
      coords: canonical system name -> (x,y,z)
      aliases: lookup_key -> [seen_name_variants]
    """
    targets = target_names[:]
    if not strict_case:
        target_keys = {t.lower(): t for t in targets}
    else:
        target_keys = {t: t for t in targets}

    found: Dict[str, Tuple[float, float, float]] = {}
    aliases: Dict[str, List[str]] = {k: [] for k in target_keys.keys()}
    remaining_keys = set(target_keys.keys())

    for cat in catalogs:
        if not cat.exists():
            continue

        it = iter_csv_rows(cat)
        try:
            header = next(it)
        except StopIteration:
            continue

        hmap = read_header_map(header)

        name_col = find_col(hmap, ["name", "system", "system_name", "star_system"])
        x_col = find_col(hmap, ["x"])
        y_col = find_col(hmap, ["y"])
        z_col = find_col(hmap, ["z"])

        if name_col is None or x_col is None or y_col is None or z_col is None:
            continue

        for row in it:
            if not remaining_keys:
                break
            if len(row) <= max(name_col, x_col, y_col, z_col):
                continue

            raw_name = row[name_col].strip()
            if not raw_name:
                continue

            key = raw_name if strict_case else raw_name.lower()
            if key not in remaining_keys:
                continue

            try:
                x = float(row[x_col])
                y = float(row[y_col])
                z = float(row[z_col])
            except Exception:
                continue

            canonical = target_keys[key]
            found[canonical] = (x, y, z)
            aliases[key].append(raw_name)
            remaining_keys.remove(key)

    return found, aliases


# ---------------------------
# Anchor helpers (v1 + v2)
# ---------------------------
def flatten_constellation_anchors(c: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Returns unified anchors: [{"system": str, "weight": float}, ...]
    Supports:
      v1: c["systems"] = ["A","B"]
      v2: c["anchor_groups"][].anchors[] = {"system": "...", "weight": ...}
    """
    out: List[Dict[str, Any]] = []

    systems = c.get("systems")
    if isinstance(systems, list):
        for s in systems:
            if isinstance(s, str) and s.strip():
                out.append({"system": s.strip(), "weight": 1.0})

    groups = c.get("anchor_groups")
    if isinstance(groups, list):
        for g in groups:
            if not isinstance(g, dict):
                continue
            anchors = g.get("anchors")
            if not isinstance(anchors, list):
                continue
            for a in anchors:
                if not isinstance(a, dict):
                    continue
                s = a.get("system")
                if not (isinstance(s, str) and s.strip()):
                    continue
                w = a.get("weight", 1.0)
                try:
                    w = float(w)
                except Exception:
                    w = 1.0
                out.append({"system": s.strip(), "weight": w})

    return out


def get_references(cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    refs = cfg.get("references", [])
    return refs if isinstance(refs, list) else []


# ---------------------------
# Vector math
# ---------------------------
def norm(v: Tuple[float, float, float]) -> float:
    return math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])


def normalize(v: Tuple[float, float, float]) -> Optional[Tuple[float, float, float]]:
    n = norm(v)
    if n <= 1e-12:
        return None
    return (v[0] / n, v[1] / n, v[2] / n)


def mean_unit_vector(vectors: List[Tuple[float, float, float]]) -> Optional[Tuple[float, float, float]]:
    if not vectors:
        return None
    sx = sum(v[0] for v in vectors)
    sy = sum(v[1] for v in vectors)
    sz = sum(v[2] for v in vectors)
    return normalize((sx, sy, sz))


# ---------------------------
# Build output JSON
# ---------------------------
def build_sky_ed_json(
    anchors_cfg: Dict[str, Any],
    coords: Dict[str, Tuple[float, float, float]],
    vector_length_default: float,
) -> Dict[str, Any]:
    nodes: List[Dict[str, Any]] = []
    links: List[Dict[str, Any]] = []

    meta = anchors_cfg.get("meta", {}) if isinstance(anchors_cfg.get("meta", {}), dict) else {}
    center = meta.get("center", "Sol")

    # Resolve Sol if it exists in coords; else assume 0,0,0 (ED convention)
    sol_xyz = coords.get(center, (0.0, 0.0, 0.0))

    nodes.append({
        "id": center,
        "label": center,
        "x": sol_xyz[0], "y": sol_xyz[1], "z": sol_xyz[2],
        "type": "origin",
        "role": "origin"
    })

    # Emit references first (e.g., Maia)
    for r in get_references(anchors_cfg):
        if not isinstance(r, dict):
            continue
        sysname = r.get("system")
        if not (isinstance(sysname, str) and sysname.strip()):
            continue
        sysname = sysname.strip()
        if sysname not in coords:
            continue

        x, y, z = coords[sysname]
        rid = r.get("id", sysname)
        rlabel = r.get("label", sysname)

        nodes.append({
            "id": rid,
            "label": rlabel,
            "x": x, "y": y, "z": z,
            "type": r.get("type", "reference"),
            "role": r.get("role", "reference"),
            "system": sysname
        })

        for lk in (r.get("links") or []):
            if not isinstance(lk, dict):
                continue
            target = lk.get("target")
            if not isinstance(target, str):
                continue
            links.append({
                "source": rid,
                "target": target,
                "kind": lk.get("kind", "reference_ray"),
                "label": lk.get("label", "")
            })

    constellations = anchors_cfg.get("constellations", [])
    if not isinstance(constellations, list):
        constellations = []

    # Track farthest node distance to suggest a wire radius
    max_dist = 0.0

    for c in constellations:
        if not isinstance(c, dict):
            continue

        cname = c.get("name", "Constellation")
        clabel = c.get("label", cname)

        try:
            vec_len = float(c.get("vector_length_ly", vector_length_default))
        except Exception:
            vec_len = vector_length_default

        anchors = flatten_constellation_anchors(c)
        used_systems: List[str] = []
        weighted_unit_vectors: List[Tuple[float, float, float]] = []

        for a in anchors:
            s = a.get("system")
            if not (isinstance(s, str) and s.strip()):
                continue
            s = s.strip()

            try:
                w = float(a.get("weight", 1.0))
            except Exception:
                w = 1.0

            if s not in coords:
                continue

            x, y, z = coords[s]
            nodes.append({
                "id": s,
                "label": s,
                "x": x, "y": y, "z": z,
                "type": "anchor",
                "role": f"sky_anchor:{cname}",
                "constellation": cname,
                "constellation_label": clabel,
                "weight": w
            })

            links.append({
                "source": center,
                "target": s,
                "kind": "ray",
                "constellation": cname
            })

            # Vector uses direction from Sol toward anchor
            dx, dy, dz = (x - sol_xyz[0], y - sol_xyz[1], z - sol_xyz[2])
            u = normalize((dx, dy, dz))
            if u:
                weighted_unit_vectors.append((u[0] * w, u[1] * w, u[2] * w))
                used_systems.append(s)

            d = norm((dx, dy, dz))
            if d > max_dist:
                max_dist = d

        avg = mean_unit_vector(weighted_unit_vectors)
        vec_id = f"{cname}__VECTOR"

        if avg:
            vx, vy, vz = (
                sol_xyz[0] + avg[0] * vec_len,
                sol_xyz[1] + avg[1] * vec_len,
                sol_xyz[2] + avg[2] * vec_len,
            )
            nodes.append({
                "id": vec_id,
                "label": f"{clabel} Direction",
                "x": vx, "y": vy, "z": vz,
                "type": "vector",
                "role": f"sky_vector:{cname}",
                "constellation": cname,
                "constellation_label": clabel,
                "anchors_used": used_systems,
                "vector_length_ly": vec_len
            })
            links.append({
                "source": center,
                "target": vec_id,
                "kind": "vector",
                "constellation": cname
            })

            dv = norm((vx - sol_xyz[0], vy - sol_xyz[1], vz - sol_xyz[2]))
            if dv > max_dist:
                max_dist = dv
        else:
            nodes.append({
                "id": vec_id,
                "label": f"{clabel} Direction (NO ANCHORS FOUND)",
                "x": sol_xyz[0], "y": sol_xyz[1], "z": sol_xyz[2],
                "type": "vector_missing",
                "role": f"sky_vector_missing:{cname}",
                "constellation": cname,
                "constellation_label": clabel,
                "anchors_used": used_systems,
                "vector_length_ly": vec_len
            })

    # A nice default radius: slightly larger than farthest anchor/vector distance
    radius = 0.0
    if max_dist > 0:
        radius = float(int(max_dist * 1.10))

    return {
        "nodes": nodes,
        "links": links,
        "meta": {
            "layer": "sky_ed",
            "center": center,
            "vector_length_ly_default": vector_length_default,
            "radius": radius,
            "notes": "Sky layer uses real Elite Dangerous coordinates (x,y,z) from local catalogs. Constellation vectors are computed from anchor directions from Sol. References (e.g., Maia) are included as special nodes."
        }
    }


# ---------------------------
# Main
# ---------------------------
def main() -> None:
    ap = argparse.ArgumentParser(description="Build an ED-coordinate 'Sky' layer from constellation anchor systems.")
    ap.add_argument("--anchors", default=str(DEFAULT_ANCHORS), help="Path to sky_constellation_anchors.json")
    ap.add_argument("--out", default=str(DEFAULT_OUT), help="Output JSON path (viewer loads this)")
    ap.add_argument("--catalog", action="append", default=[], help="Additional CSV catalog(s) to search for system coords")
    ap.add_argument("--vector-length", type=float, default=None, help="Default vector length (ly) for constellation direction rays")
    ap.add_argument("--strict-case", action="store_true", help="Match system names case-sensitively (default: case-insensitive)")
    args = ap.parse_args()

    anchors_path = Path(args.anchors)
    out_path = Path(args.out)

    if not anchors_path.exists():
        raise SystemExit(f"Missing anchors file: {anchors_path}")

    anchors_cfg: Dict[str, Any] = json.loads(anchors_path.read_text(encoding="utf-8"))

    meta = anchors_cfg.get("meta", {}) if isinstance(anchors_cfg.get("meta", {}), dict) else {}
    vector_length_default = args.vector_length
    if vector_length_default is None:
        vector_length_default = float(meta.get("vector_length_ly_default", meta.get("vector_length_ly", 1200)))

    catalogs = DEFAULT_CATALOGS + [Path(p) for p in args.catalog]
    catalogs = [c for c in catalogs if c.exists()]

    # Gather target names FIRST (constellation anchors + references + center)
    target_names: List[str] = []

    center = str(meta.get("center", "Sol"))
    if center:
        target_names.append(center)

    constellations = anchors_cfg.get("constellations", [])
    if not isinstance(constellations, list):
        constellations = []

    for c in constellations:
        if not isinstance(c, dict):
            continue
        for a in flatten_constellation_anchors(c):
            s = a.get("system")
            if isinstance(s, str) and s.strip():
                target_names.append(s.strip())

    for r in get_references(anchors_cfg):
        if isinstance(r, dict):
            s = r.get("system")
            if isinstance(s, str) and s.strip():
                target_names.append(s.strip())

    target_names = sorted(set(target_names))
    if not target_names:
        raise SystemExit("No systems listed in anchors file (constellations or references).")

    print("[INFO] Catalogs searched (in order):")
    for c in catalogs:
        print(f"  - {c}")

    coords, _aliases = load_coords_from_catalogs(target_names, catalogs, strict_case=args.strict_case)

    # Report misses (constellations)
    print("\n[INFO] Anchor resolution:")
    total_found = 0
    total_missed = 0

    for c in constellations:
        cname = c.get("name", "Constellation")
        systems = [a["system"] for a in flatten_constellation_anchors(c)]

        found = [s for s in systems if s in coords]
        missed = [s for s in systems if s not in coords]

        total_found += len(found)
        total_missed += len(missed)

        print(f"\n  {cname}:")
        print(f"    found:  {len(found)}")
        for s in found:
            x, y, z = coords[s]
            print(f"      - {s}  ({x:.2f}, {y:.2f}, {z:.2f})")
        print(f"    missed: {len(missed)}")
        for s in missed:
            print(f"      - {s}")

    # Report reference resolution
    refs = get_references(anchors_cfg)
    if refs:
        print("\n[INFO] References:")
        for r in refs:
            if not isinstance(r, dict):
                continue
            sysname = r.get("system")
            rid = r.get("id", sysname)
            if isinstance(sysname, str) and sysname.strip() and sysname.strip() in coords:
                x, y, z = coords[sysname.strip()]
                print(f"  - {rid}: {sysname.strip()}  ({x:.2f}, {y:.2f}, {z:.2f})")
            else:
                print(f"  - {rid}: (missing) {sysname}")

    print(f"\n[SUMMARY] Unique targets: {len(target_names)} | Found: {len(coords)} | Missed: {len(target_names) - len(coords)}")
    print(f"[SUMMARY] Constellation anchors | Found: {total_found} | Missed: {total_missed}")

    out = build_sky_ed_json(anchors_cfg, coords, vector_length_default)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")

    print(f"\n[DONE] Wrote sky layer -> {out_path}")
    print("[NEXT] Open: http://localhost:8000/web/unified_map2.html")
    print("[NEXT] Ensure you serve from project root: python -m http.server 8000")


if __name__ == "__main__":
    main()
