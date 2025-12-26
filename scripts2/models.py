from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Dict, Any, List, Tuple


@dataclass
class SystemNode:
    """Represents a system or site in a hunt graph."""
    name: str
    x: Optional[float] = None
    y: Optional[float] = None
    z: Optional[float] = None
    category: str = "unknown"  # e.g. "permit_locked", "anomaly", "lore_hub", "guardian_shell"
    region: Optional[str] = None  # e.g. "Formidine Rift", "Guardian_Shell"
    faction: Optional[str] = None  # e.g. "Dark Wheel", "October Consortium"
    notes: Optional[str] = None

    def has_coords(self) -> bool:
        return self.x is not None and self.y is not None and self.z is not None

    def coords(self) -> Optional[Tuple[float, float, float]]:
        if not self.has_coords():
            return None
        return float(self.x), float(self.y), float(self.z)


@dataclass
class JumpEvent:
    """
    Represents a single witch-space jump and any observed anomalies.
    Stored in a JSONL file for accumulation over time.
    """
    timestamp_utc: str  # ISO 8601 string
    origin: str
    destination: str

    origin_coords: Optional[Tuple[float, float, float]] = None
    destination_coords: Optional[Tuple[float, float, float]] = None

    cargo: Optional[List[str]] = None          # e.g. ["Guardian Relic", "Unclassified Relic"]
    ship: Optional[str] = None                 # e.g. "Krait Phantom"
    fsd_type: Optional[str] = None             # e.g. "A5, Guardian Booster"
    notes: Optional[str] = None                # freeform

    anomaly_visual: bool = False
    anomaly_audio: bool = False
    anomaly_duration: bool = False

    extra: Optional[Dict[str, Any]] = None     # anything else


@dataclass
class LoreText:
    """Represents a piece of lore we want to analyze as potential cipher/map."""
    identifier: str
    title: str
    source: str      # e.g. "Codex", "Tourist Beacon", "Children's Book"
    body: str
