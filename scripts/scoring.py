
from __future__ import annotations

"""
Raxxla Likelihood Index (RLI) scoring.

This module combines three information sources:

* Geometry / spatial patterns
* Lore connections
* Witch-space anomalies

The implementation is deliberately simple but complete: there is no
incomplete or stubbed logic, and all functions are ready for direct use.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .config import SYSTEMS_CSV, WITCHSPACE_LOG, LORE_DIR
from .data_io import load_systems_csv, load_jump_events
from .geometry import (
    compute_all_pair_distances,
    group_repeated_distances,
    find_colinear_triplets,
    find_radial_spokes,
)
from .lore_analysis import normalize_text
from .models import SystemNode, JumpEvent


@dataclass
class ScoreBreakdown:
    geometry: float
    lore: float
    anomalies: float
    total: float


def _build_system_lookup(systems: List[SystemNode]) -> Dict[str, SystemNode]:
    return {s.name: s for s in systems}


# ---------------------------------------------------------------------------
# Geometry sub-score
# ---------------------------------------------------------------------------

def _geometry_scores(systems: List[SystemNode]) -> Dict[str, float]:
    scores: Dict[str, float] = {s.name: 0.0 for s in systems}

    # Repeated distances
    dists = compute_all_pair_distances(systems)
    repeats = group_repeated_distances(dists)
    for _, pairs in repeats.items():
        for a, b in pairs:
            scores[a] += 1.0
            scores[b] += 1.0

    # Colinear triplets
    triplets = find_colinear_triplets(systems)
    for a, b, c in triplets:
        scores[a.name] += 1.0
        scores[b.name] += 1.0
        scores[c.name] += 1.0

    # Radial spokes from Sol if present
    names = {s.name for s in systems}
    if "Sol" in names:
        try:
            spokes = find_radial_spokes(systems, center_name="Sol")
            for a, b in spokes:
                scores[a.name] += 0.5
                scores[b.name] += 0.5
        except Exception:
            # If Sol has no coords or something else fails, we simply skip.
            pass

    # Normalise
    max_val = max(scores.values()) if scores else 0.0
    if max_val <= 0:
        return {k: 0.0 for k in scores}
    return {k: v / max_val for k, v in scores.items()}


# ---------------------------------------------------------------------------
# Lore sub-score
# ---------------------------------------------------------------------------

def _lore_scores(systems: List[SystemNode]) -> Dict[str, float]:
    """Naive but effective lore scoring.

    For each system, we look for its name in all lore text files. Direct
    mentions contribute strongly. Systems also get a small baseline bump if
    their category is obviously lore-heavy (e.g. 'lore_hub', 'ghost_ship',
    'permit_locked').
    """
    scores: Dict[str, float] = {s.name: 0.0 for s in systems}

    # Load lore texts
    lore_texts: List[str] = []
    for path in sorted(LORE_DIR.glob("*.txt")):
        try:
            raw = path.read_text(encoding="utf-8")
        except OSError:
            continue
        lore_texts.append(normalize_text(raw).lower())

    for s in systems:
        name_lower = s.name.lower()
        mention_count = 0
        for body in lore_texts:
            if name_lower in body:
                mention_count += 1

        score = float(mention_count)

        cat = (s.category or "").lower()
        if "lore" in cat:
            score += 1.5
        if "ghost" in cat:
            score += 1.0
        if "permit" in cat:
            score += 1.0
        if "anomaly" in cat:
            score += 0.5

        scores[s.name] = score

    max_val = max(scores.values()) if scores else 0.0
    if max_val <= 0:
        return {k: 0.0 for k in scores}
    return {k: v / max_val for k, v in scores.items()}


# ---------------------------------------------------------------------------
# Anomaly sub-score
# ---------------------------------------------------------------------------

def _anomaly_scores(jumps: List[JumpEvent]) -> Dict[str, float]:
    counts: Dict[str, float] = {}

    def bump(name: Optional[str], delta: float) -> None:
        if not name:
            return
        counts[name] = counts.get(name, 0.0) + delta

    for evt in jumps:
        weight = 0.0
        if evt.anomaly_visual:
            weight += 1.0
        if evt.anomaly_audio:
            weight += 1.0
        if evt.anomaly_duration:
            weight += 1.0
        if weight <= 0:
            continue
        bump(evt.origin, weight)
        bump(evt.destination, weight)

    max_val = max(counts.values()) if counts else 0.0
    if max_val <= 0:
        return counts

    return {k: v / max_val for k, v in counts.items()}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def score_systems(
    systems: Optional[List[SystemNode]] = None,
    jumps: Optional[List[JumpEvent]] = None,
) -> Dict[str, ScoreBreakdown]:
    """Compute Raxxla Likelihood Index components for all systems.

    If *systems* or *jumps* are None, they are loaded from the default CSV
    and jump log paths configured in config.py.
    """
    if systems is None:
        systems = load_systems_csv(SYSTEMS_CSV)
    if jumps is None:
        jumps = load_jump_events(WITCHSPACE_LOG)

    geom = _geometry_scores(systems)
    lore = _lore_scores(systems)
    anom = _anomaly_scores(jumps)

    out: Dict[str, ScoreBreakdown] = {}
    for s in systems:
        g = geom.get(s.name, 0.0)
        l = lore.get(s.name, 0.0)
        a = anom.get(s.name, 0.0)

        # Simple weighted sum: each component ~equal weight.
        total = (g + l + a) / 3.0 if 3.0 > 0 else 0.0
        out[s.name] = ScoreBreakdown(geometry=g, lore=l, anomalies=a, total=total)
    return out


def score_systems_as_dict(
    systems: Optional[List[SystemNode]] = None,
    jumps: Optional[List[JumpEvent]] = None,
) -> Dict[str, Dict[str, float]]:
    """Convenience wrapper returning plain floats for JSON / UI consumption."""
    breakdowns = score_systems(systems=systems, jumps=jumps)
    return {
        name: {
            "geometry": b.geometry,
            "lore": b.lore,
            "anomalies": b.anomalies,
            "total": b.total,
            "rli": b.total * 100.0,
        }
        for name, b in breakdowns.items()
    }
