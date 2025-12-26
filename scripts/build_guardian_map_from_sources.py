from __future__ import annotations

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

COORD_BACKFILL_CSV = ROOT / "data" / "guardian_systems.csv"  # optional backfill
OUT_JSON = ROOT / "data" / "processed" / "guardian_map.json"


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def to_float(v: Any) -> Optional[float]:
    try:
        if v is None or isinstance(v, bool):
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
        f = to_float(d.get(k))
        if f is not None:
            return f
    return None


def extract_xyz(obj: Any) -> Tuple[Optional[float], Optional[float], Optional[float]]:
    if not isinstance(obj, dict):
        return (None, None, None)

    x = first_num(obj, ["x", "X"])
    y = first_num(obj, ["y", "Y"])
    z = first_num(obj, ["z", "Z"])
    if x is not None or y is not None or z is not None:
        return (x, y, z)

    for k in ["coords", "coord", "coordinates", "pos", "position", "location"]:
        v = obj.get(k)
        if isinstance(v, dict):
            x = first_num(v, ["x", "X"])
            y = first_num(v, ["y", "Y"])
            z = first_num(v, ["z", "Z"])
            if x is not None or y is not None or z is not None:
                return (x, y, z)
        if isinstance(v, (list, tuple)) and len(v) >= 3:
            x = to_float(v[0]); y = to_float(v[1]); z = to_float(v[2])
            if x is not None or y is not None or z is not None:
                return (x, y, z)

    return (None, None, None)


def iter_records(root: Any) -> Iterable[Dict[str, Any]]:
    if isinstance(root, list):
        for it in root:
            if isinstance(it, dict):
                yield it
        return

    if isinstance(root, dict):
        if isinstance(root.get("nodes"), list):
            for it in root["nodes"]:
                if isinstance(it, dict):
                    yield it
            return

        for k in ["items", "data", "records", "features", "results", "rows", "hotspots", "systems"]:
            v = root.get(k)
            if isinstance(v, list):
                for it in v:
                    if isinstance(it, dict):
                        yield it
                return

        vals = list(root.values())
        if vals and all(isinstance(v, dict) for v in vals):
            for v in vals:
                yield v
            return


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
    name = first_str(rec, ["system", "system_name", "System", "StarSystem", "name", "id", "label"])

    if not name:
        sys_obj = rec.get("system")
        if isinstance(sys_obj, dict):
            name = first_str(sys_obj, ["name", "system", "id", "label"])

    if not name:
        return None

    x, y, z = extract_xyz(rec)
    if (x is None and y is None and z is None) and isinstance(rec.get("system"), dict):
        x2, y2, z2 = extract_xyz(rec["system"])
        x = x2 if x is None else x
        y = y2 if y is None else y
        z = z2 if z is None else z

    role = first_str(rec, ["role", "category", "type", "kind", "class"]) or source_name.replace(".json", "")
    score = first_num(rec, ["score", "weight", "prob", "probability", "density", "rank", "gmm_score", "corr_score"])

    return Node(
        id=name,
        label=name,
        x=x if x is not None else 0.0,
        y=y if y is not None else 0.0,
        z=z if z is not None else 0.0,
        role=role,
        sources=[source_name],
        score=score,
    )


def load_coord_backfill(csv_path: Path) -> Dict[str, Tuple[float, float, float]]:
    if not csv_path.exists():
        return {}
    out: Dict[str, Tuple[float, float, float]] = {}
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
            out[name] = (x, y, z)
    return out


def merge_nodes(a: Node, b: Node) -> Node:
    a_unknown = (a.x == 0.0 and a.y == 0.0 and a.z == 0.0)
    b_unknown = (b.x == 0.0 and b.y == 0.0 and b.z == 0.0)

    x, y, z = a.x, a.y, a.z
    if a_unknown and not b_unknown:
        x, y, z = b.x, b.y, b.z

    role = a.role if a.role else b.role
    sources = sorted(set(a.sources + b.sources))

    score = a.score
    if b.score is not None:
        score = b.score if score is None else max(score, b.score)

    return Node(
        id=a.id,
        label=a.label,
        x=x, y=y, z=z,
        role=role,
        sources=sources,
        score=score,
    )


def main() -> None:
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)

    backfill = load_coord_backfill(COORD_BACKFILL_CSV)
    print(f"[INFO] Coord backfill: {len(backfill)} rows from {COORD_BACKFILL_CSV.name}" if backfill else
          f"[WARN] No coord backfill found at {COORD_BACKFILL_CSV}")

    nodes: Dict[str, Node] = {}

    for src in SOURCES:
        if not src.exists():
            print(f"[WARN] Missing source: {src}")
            continue

        root = read_json(src)
        rec_count = node_count = skip_count = 0

        for rec in iter_records(root):
            rec_count += 1
            node = normalize_record(rec, src.name)
            if node is None:
                skip_count += 1
                continue

            # backfill coords if unknown
            if node.x == 0.0 and node.y == 0.0 and node.z == 0.0 and node.id in backfill:
                bx, by, bz = backfill[node.id]
                node.x, node.y, node.z = bx, by, bz

            if node.id in nodes:
                nodes[node.id] = merge_nodes(nodes[node.id], node)
            else:
                nodes[node.id] = node

            node_count += 1

        print(f"[OK] {src.name}: records={rec_count} nodes={node_count} skipped={skip_count}")

    nodes_out: List[Dict[str, Any]] = []
    for n in nodes.values():
        d = {
            "id": n.id,
            "label": n.label,
            "x": n.x, "y": n.y, "z": n.z,
            "role": n.role,
            "sources": n.sources,
        }
        if n.score is not None:
            d["score"] = n.score
        nodes_out.append(d)

    out = {
        "nodes": sorted(nodes_out, key=lambda d: d["id"].lower()),
        "links": [],
        "meta": {
            "layer": "guardian",
            "center": "Sol",
            "sources": [p.name for p in SOURCES],
            "coord_backfill": COORD_BACKFILL_CSV.name if COORD_BACKFILL_CSV.exists() else None,
            "notes": "Merged from guardian_sources JSONs; coords backfilled from guardian_systems.csv when possible."
        }
    }

    OUT_JSON.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"\n[DONE] Wrote -> {OUT_JSON}")
    print(f"[INFO] Unique nodes: {len(nodes_out)}")


if __name__ == "__main__":
    main()
