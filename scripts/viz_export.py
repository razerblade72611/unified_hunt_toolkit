from __future__ import annotations
import json
from pathlib import Path
from typing import List, Dict, Any, Tuple, Set

from .models import SystemNode
from .geometry import distance


def _serialize_node(s: SystemNode) -> Dict[str, Any]:
    x, y, z = (None, None, None)
    if s.has_coords():
        x, y, z = s.coords()

    return {
        "id": s.name,
        "name": s.name,
        "x": x,
        "y": y,
        "z": z,
        "category": s.category,
        "region": s.region,
        "faction": s.faction,
        "notes": s.notes,
    }


def _compute_knn_links(
    systems: List[SystemNode],
    k: int = 3,
) -> List[Dict[str, Any]]:
    coords_systems = [s for s in systems if s.has_coords()]
    links: List[Dict[str, Any]] = []

    if len(coords_systems) < 2:
        return links

    for i, s in enumerate(coords_systems):
        dists: List[Tuple[float, SystemNode]] = []
        for j, t in enumerate(coords_systems):
            if i == j:
                continue
            d = distance(s, t)
            dists.append((d, t))
        dists.sort(key=lambda x: x[0])
        for d, t in dists[:k]:
            a = min(s.name, t.name)
            b = max(s.name, t.name)
            links.append(
                {
                    "source": a,
                    "target": b,
                    "distance": d,
                }
            )

    seen: Set[Tuple[str, str]] = set()
    deduped: List[Dict[str, Any]] = []
    for link in links:
        key = (link["source"], link["target"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(link)
    return deduped


def export_systems_to_json(
    systems: List[SystemNode],
    path: Path,
    add_links: bool = True,
    k_neighbors: int = 3,
    meta: Dict[str, Any] | None = None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    nodes = [_serialize_node(s) for s in systems]

    links: List[Dict[str, Any]] = []
    if add_links:
        links = _compute_knn_links(systems, k=k_neighbors)

    if meta is None:
        meta = {}

    payload = {
        "meta": {
            "description": "Hunt visualization export",
            "node_count": len(nodes),
            "link_count": len(links),
            **meta,
        },
        "nodes": nodes,
        "links": links,
    }

    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    print(f"Exported {len(nodes)} nodes and {len(links)} links to {path}")
