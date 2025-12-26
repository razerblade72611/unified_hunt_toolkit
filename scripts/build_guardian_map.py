# scripts/download_raw_data.py

import gzip
import sys
from pathlib import Path

import requests
from tqdm import tqdm

# Import config paths and URLs
sys.path.append(str(Path(__file__).resolve().parents[1]))
from config import (
    EDSM_RAW_DIR,
    EDASTRO_RAW_DIR,
    CANONN_RAW_DIR,
    EDSM_URLS,
    EDASTRO_URLS,
    CANONN_URLS,
)

def ensure_dirs():
    for d in (EDSM_RAW_DIR, EDASTRO_RAW_DIR, CANONN_RAWfrom __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]

SOURCES = [
    ROOT / "data" / "guardian_sources" / "guardian_known_seed.json",
    ROOT / "data" / "guardian_sources" / "potential_guardian_hotspots_GMM.json",
    ROOT / "data" / "guardian_sources" / "potential_guardian_hotspots_CORR.json",
    ROOT / "data" / "guardian_sources" / "guardian_ruins_and_structures.json",
]

COORD_BACKFILL_CSV = ROOT / "data" / "guardian_systems.csv"  # optional but recommended
OUT_JSON = ROOT / "data" / "processed" / "guardian_map.json"


# ----------------------------
# Helpers
# ----------------------------
def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))

def to_float(v: Any) -> Optional[float]:
    try:
        if v is None:
            return None
        if isinstance(v, bool):
            return None
        return float(v)
    except Exception:
        return None

def first_str(d: Dict[str, Any], keys: List[str]) -> Optional[str]:
    for k in keys:
        v = d.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return None

def first_num(d: Dict[str, Any], keys: List[str]) -> Optional[float]:
    for k in keys:
        v = d.get(k)
        f = to_float(v)
        if f is not None:
            return f
    return None

def extract_xyz(obj: Any) -> Tuple[Optional[float], Optional[float], Optional[float]]:
    """
    Accepts a dict (with x/y/z, X/Y/Z, coords, coordinates, position, etc.)
    Returns (x,y,z) if found, else (None,None,None)
    """
    if not isinstance(obj, dict):
        return (None, None, None)

    # direct keys
    x = first_num(obj, ["x", "X"])
    y = first_num(obj, ["y", "Y"])
    z = first_num(obj, ["z", "Z"])
    if x is not None or y is not None or z is not None:
        return (x, y, z)

    # nested coords-like dict
    for k in ["coords", "coord", "coordinates", "pos", "position", "location"]:
        v = obj.get(k)
        if isinstance(v, dict):
            x = first_num(v, ["x", "X", "0"])
            y = first_num(v, ["y", "Y", "1"])
            z = first_num(v, ["z", "Z", "2"])
            if x is not None or y is not None or z is not None:
                return (x, y, z)

        # position sometimes list/tuple [x,y,z]
        if isinstance(v, (list, tuple)) and len(v) >= 3:
            x = to_float(v[0]); y = to_float(v[1]); z = to_float(v[2])
            if x is not None or y is not None or z is not None:
                return (x, y, z)

    return (None, None, None)

def iter_records(root: Any) -> Iterable[Dict[str, Any]]:
    """
    Turns various JSON shapes into a stream of dict records.
    - list[dict]
    - dict with a single list field (items/features/data/records/etc.)
    - dict-of-dicts (values are dict records)
    """
    if isinstance(root, list):
        for it in root:
            if isinstance(it, dict):
                yield it
        return

    if isinstance(root, dict):
        # If this already looks like our {nodes:[...], links:[...]} format, treat nodes as records
        if isinstance(root.get("nodes"), list):
            for it in root["nodes"]:
                if isinstance(it, dict):
                    yield it
            return

        # Common container keys
        for k in ["items", "data", "records", "features", "results", "rows", "hotspots", "systems"]:
            v = root.get(k)
            if isinstance(v, list):
                for it in v:
                    if isinstance(it, dict):
                        yield it
                return

        # If values are dicts, yield them
        dict_values = list(root.values())
        if dict_values and all(isinstance(v, dict) for v in dict_values):
            for v in dict_values:
                yield v
            return

    # otherwise nothing

@dataclass
class Node:
    id: str
    label: str
    x: float
    y: float
    z: float
    role: str
    sources: List[str]
    score: Optional[float] = None

def normalize_record(rec: Dict[str, Any], source_name: str) -> Optional[Node]:
    # name/system/id fields (flexible)
    name = (
        first_str(rec, ["system", "system_name", "System", "StarSystem", "name", "id", "label"])
        or None
    )

    # Sometimes name is nested (e.g., rec["system"]["name"])
    if not name:
        sys_obj = rec.get("system")
        if isinstance(sys_obj, dict):
            name = first_str(sys_obj, ["name", "system", "id", "label"])

    if not name:
        return None

    x, y, z = extract_xyz(rec)
    # Some records store coords nested under "system"
    if (x is None and y is None and z is None) and isinstance(rec.get("system"), dict):
        x2, y2, z2 = extract_xyz(rec["system"])
        x = x2 if x is None else x
        y = y2 if y is None else y
        z = z2 if z is None else z

    # role/category (flexible)
    role = (
        first_str(rec, ["role", "category", "type", "kind", "class"])
        or source_name.replace(".json", "")
    )

    # score (optional)
    score = first_num(rec, ["score", "weight", "prob", "probability", "density", "rank", "gmm_score", "corr_score"])

    # if coords missing, temporarily set 0; we may backfill later
    nx = x if x is not None else 0.0
    ny = y if y is not None else 0.0
    nz = z if z is not None else 0.0

    return Node(
        id=name,
        label=name,
        x=nx, y=ny, z=nz,
        role=role,
        sources=[source_name],
        score=score,
    )

def load_coord_backfill(csv_path: Path) -> Dict[str, Tuple[float, float, float]]:
    """
    Loads guardian_systems.csv mapping: name -> (x,y,z)
    Accepts flexible headers.
    """
    if not csv_path.exists():
        return {}

    mapping: Dict[str, Tuple[float, float, float]] = {}
    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            name = (row.get("name") or row.get("system") or row.get("System") or row.get("id") or "").strip()
            if not name:
                continue
            x = to_float(row.get("x") or row.get("X"))
            y = to_float(row.get("y") or row.get("Y"))
            z = to_float(row.get("z") or row.get("Z"))
            if x is None or y is None or z is None:
                continue
            mapping[name] = (x, y, z)
    return mapping

def merge_nodes(existing: Node, incoming: Node) -> Node:
    """
    Prefer nodes that have non-zero coords over zero coords.
    Merge sources, keep best score if present.
    """
    # coords heuristic: treat (0,0,0) as "unknown" unless truly intended
    existing_unknown = (existing.x == 0.0 and existing.y == 0.0 and existing.z == 0.0)
    incoming_unknown = (incoming.x == 0.0 and incoming.y == 0.0 and incoming.z == 0.0)

    x, y, z = existing.x, existing.y, existing.z
    if existing_unknown and not incoming_unknown:
        x, y, z = incoming.x, incoming.y, incoming.z

    # merge role: keep existing unless it's generic and incoming looks better
    role = existing.role
    if (role == "guardian" or role.startswith("potential_guardian")) and incoming.role and incoming.role != role:
        role = incoming.role

    sources = sorted(set(existing.sources + incoming.sources))

    score = existing.score
    if incoming.score is not None:
        if score is None:
            score = incoming.score
        else:
            # keep max score (simple heuristic)
            score = max(score, incoming.score)

    return Node(
        id=existing.id,
        label=existing.label,
        x=x, y=y, z=z,
        role=role,
        sources=sources,
        score=score,
    )

def main() -> None:
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)

    backfill = load_coord_backfill(COORD_BACKFILL_CSV)
    if backfill:
        print(f"[INFO] Coord backfill loaded: {len(backfill)} systems from {COORD_BACKFILL_CSV.name}")
    else:
        print(f"[WARN] No coord backfill found (or empty): {COORD_BACKFILL_CSV}")

    nodes_by_id: Dict[str, Node] = {}
    per_file_counts: Dict[str, Dict[str, int]] = {}

    for src in SOURCES:
        name = src.name
        per_file_counts[name] = {"records": 0, "nodes": 0, "skipped": 0}
        if not src.exists():
            print(f"[WARN] Missing source file: {src}")
            continue

        root = read_json(src)
        for rec in iter_records(root):
            per_file_counts[name]["records"] += 1
            node = normalize_record(rec, name)
            if node is None:
                per_file_counts[name]["skipped"] += 1
                continue

            # Backfill coords if still unknown
            if node.x == 0.0 and node.y == 0.0 and node.z == 0.0:
                if node.id in backfill:
                    bx, by, bz = backfill[node.id]
                    node.x, node.y, node.z = bx, by, bz

            if node.id in nodes_by_id:
                nodes_by_id[node.id] = merge_nodes(nodes_by_id[node.id], node)
            else:
                nodes_by_id[node.id] = node

            per_file_counts[name]["nodes"] += 1

        print(f"[OK] Loaded {name}: records={per_file_counts[name]['records']} nodes={per_file_counts[name]['nodes']} skipped={per_file_counts[name]['skipped']}")

    # Final pass: attempt backfill for any remaining unknown coords
    filled = 0
    for k, n in list(nodes_by_id.items()):
        if (n.x == 0.0 and n.y == 0.0 and n.z == 0.0) and (k in backfill):
            bx, by, bz = backfill[k]
            n.x, n.y, n.z = bx, by, bz
            nodes_by_id[k] = n
            filled += 1

    # Build output schema expected by viewer
    nodes_out: List[Dict[str, Any]] = []
    for n in nodes_by_id.values():
        nd = {
            "id": n.id,
            "label": n.label,
            "x": n.x,
            "y": n.y,
            "z": n.z,
            "role": n.role,
            "sources": n.sources,
        }
        if n.score is not None:
            nd["score"] = n.score
        nodes_out.append(nd)

    # Optional: create simple links between same-system nodes? (not needed; nodes-only works)
    links_out: List[Dict[str, Any]] = []

    out = {
        "nodes": sorted(nodes_out, key=lambda d: d["id"].lower()),
        "links": links_out,
        "meta": {
            "layer": "guardian",
            "center": "Sol",
            "sources": [p.name for p in SOURCES],
            "coord_backfill": COORD_BACKFILL_CSV.name if COORD_BACKFILL_CSV.exists() else None,
            "notes": "Merged from guardian_sources JSONs; coords backfilled from guardian_systems.csv when possible."
        }
    }

    OUT_JSON.write_text(json.dumps(out, indent=2), encoding="utf-8")

    print(f"\n[DONE] Wrote guardian_map.json -> {OUT_JSON}")
    print(f"[INFO] Unique nodes: {len(nodes_out)}")
    print(f"[INFO] Backfill applied in final pass: {filled}")
    print("[INFO] If many nodes are still at (0,0,0), those source files likely lack x/y/z and need coordinate enrichment.")

if __name__ == "__main__":
    main()
_DIR):
        d.mkdir(parents=True, exist_ok=True)


def download_file(url: str, dest: Path, chunk_size: int = 8192) -> None:
    """
    Stream-download a file with a progress bar.
    If the file already exists, skip by default.
    """
    if dest.exists():
        print(f"[SKIP] {dest} already exists")
        return

    print(f"[DL] {url} -> {dest}")
    dest.parent.mkdir(parents=True, exist_ok=True)

    with requests.get(url, stream=True, timeout=60) as r:
        r.raise_for_status()
        total = int(r.headers.get("content-length", 0))
        progress = tqdm(
            total=total,
            unit="B",
            unit_scale=True,
            unit_divisor=1024,
            desc=dest.name,
        )
        with open(dest, "wb") as f:
            for chunk in r.iter_content(chunk_size=chunk_size):
                if chunk:
                    f.write(chunk)
                    progress.update(len(chunk))
        progress.close()


def download_edsm():
    print("\n=== Downloading EDSM nightly dumps ===")
    for filename, url in EDSM_URLS.items():
        dest = EDSM_RAW_DIR / filename
        download_file(url, dest)


def download_edastro():
    print("\n=== Downloading EDastro CSVs ===")
    for filename, url in EDASTRO_URLS.items():
        dest = EDASTRO_RAW_DIR / filename
        download_file(url, dest)


def download_canonn():
    print("\n=== Downloading Canonn dumps ===")
    for filename, url in CANONN_URLS.items():
        # Skip placeholder Google Sheets URLs that still have 'Id' in them
        if "Id/export" in url:
            print(f"[WARN] Placeholder URL for {filename}; please update in config.py")
            continue
        dest = CANONN_RAW_DIR / filename
        download_file(url, dest)


def main():
    ensure_dirs()
    download_edsm()
    download_edastro()
    download_canonn()
    print("\nDone. Raw data in ./data/raw/")


if __name__ == "__main__":
    main()
