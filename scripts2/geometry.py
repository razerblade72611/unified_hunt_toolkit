from __future__ import annotations
import math
from dataclasses import dataclass
from typing import List, Tuple, Dict

from .models import SystemNode
from .config import DISTANCE_EPSILON, COLINEAR_EPSILON


@dataclass
class DistanceRecord:
    a: str
    b: str
    distance: float


def distance(a: SystemNode, b: SystemNode) -> float:
    if not a.has_coords() or not b.has_coords():
        raise ValueError("Both systems must have coordinates for distance()")
    ax, ay, az = a.coords()
    bx, by, bz = b.coords()
    dx = ax - bx
    dy = ay - by
    dz = az - bz
    return math.sqrt(dx * dx + dy * dy + dz * dz)


def compute_all_pair_distances(systems: List[SystemNode]) -> List[DistanceRecord]:
    coords_systems = [s for s in systems if s.has_coords()]
    out: List[DistanceRecord] = []
    for i in range(len(coords_systems)):
        for j in range(i + 1, len(coords_systems)):
            d = distance(coords_systems[i], coords_systems[j])
            out.append(
                DistanceRecord(
                    a=coords_systems[i].name,
                    b=coords_systems[j].name,
                    distance=d,
                )
            )
    return out


def group_repeated_distances(distances_list: List[DistanceRecord], tol: float = DISTANCE_EPSILON
                             ) -> Dict[float, List[Tuple[str, str]]]:
    """
    Group pairs with approximately equal distances, rounded to a tolerance.
    Returns mapping of representative distance -> list of (systemA, systemB).
    """
    buckets: Dict[float, List[Tuple[str, str]]] = {}
    for rec in distances_list:
        key = round(rec.distance / tol) * tol
        buckets.setdefault(key, []).append((rec.a, rec.b))
    return {k: v for k, v in buckets.items() if len(v) > 1}


def triangle_area(a: Tuple[float, float, float],
                  b: Tuple[float, float, float],
                  c: Tuple[float, float, float]) -> float:
    """
    Area of triangle via cross product (0.5 * |(b-a) x (c-a)|)
    """
    ab = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
    ac = (c[0] - a[0], c[1] - a[1], c[2] - a[2])
    cross = (
        ab[1] * ac[2] - ab[2] * ac[1],
        ab[2] * ac[0] - ab[0] * ac[2],
        ab[0] * ac[1] - ab[1] * ac[0],
    )
    area = 0.5 * math.sqrt(cross[0] ** 2 + cross[1] ** 2 + cross[2] ** 2)
    return area


def find_colinear_triplets(systems: List[SystemNode],
                           eps: float = COLINEAR_EPSILON) -> List[Tuple[SystemNode, SystemNode, SystemNode]]:
    """
    Rough detection of triplets of systems forming nearly straight lines.
    """
    coords_systems = [s for s in systems if s.has_coords()]
    triplets: List[Tuple[SystemNode, SystemNode, SystemNode]] = []
    n = len(coords_systems)
    for i in range(n):
        for j in range(i + 1, n):
            for k in range(j + 1, n):
                a = coords_systems[i]
                b = coords_systems[j]
                c = coords_systems[k]
                area = triangle_area(a.coords(), b.coords(), c.coords())
                if area < eps:
                    triplets.append((a, b, c))
    return triplets


def find_radial_spokes(systems: List[SystemNode],
                       center_name: str,
                       angle_tolerance_deg: float = 1.0
                       ) -> List[Tuple[SystemNode, SystemNode]]:
    """
    Given a 'center' system (e.g. Sol, Polaris, HIP 22460),
    find pairs of systems that line up in nearly the same direction from that center.
    """
    lookup = {s.name: s for s in systems}
    if center_name not in lookup:
        raise ValueError(f"Center system '{center_name}' not found in systems list")

    center = lookup[center_name]
    if not center.has_coords():
        raise ValueError(f"Center system '{center_name}' has no coordinates")

    cx, cy, cz = center.coords()

    vectors = []
    for s in systems:
        if s.name == center_name or not s.has_coords():
            continue
        x, y, z = s.coords()
        vx = x - cx
        vy = y - cy
        vz = z - cz
        mag = math.sqrt(vx * vx + vy * vy + vz * vz)
        if mag == 0:
            continue
        vectors.append((s, (vx / mag, vy / mag, vz / mag)))

    spokes: List[Tuple[SystemNode, SystemNode]] = []
    cos_tol = math.cos(math.radians(angle_tolerance_deg))
    for i in range(len(vectors)):
        s1, v1 = vectors[i]
        for j in range(i + 1, len(vectors)):
            s2, v2 = vectors[j]
            dot = v1[0] * v2[0] + v1[1] * v2[1] + v1[2] * v2[2]
            if dot >= cos_tol:
                spokes.append((s1, s2))
    return spokes
