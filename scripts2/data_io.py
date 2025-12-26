from __future__ import annotations
import csv
import json
from pathlib import Path
from typing import Iterable, List

from .models import SystemNode, JumpEvent, LoreText


def load_systems_csv(path: Path) -> List[SystemNode]:
    systems: List[SystemNode] = []
    if not path.exists():
        raise FileNotFoundError(f"Systems CSV not found: {path}")

    with path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            def parse_float(key: str):
                value = row.get(key) or ""
                return float(value) if value.strip() else None

            systems.append(
                SystemNode(
                    name=row.get("name", "").strip(),
                    x=parse_float("x"),
                    y=parse_float("y"),
                    z=parse_float("z"),
                    category=row.get("category", "unknown").strip() or "unknown",
                    region=row.get("region", "").strip() or None,
                    faction=row.get("faction", "").strip() or None,
                    notes=row.get("notes", "").strip() or None,
                )
            )
    return systems


def write_systems_csv(path: Path, systems: Iterable[SystemNode]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["name", "x", "y", "z", "category", "region", "faction", "notes"]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for s in systems:
            writer.writerow(
                {
                    "name": s.name,
                    "x": s.x if s.x is not None else "",
                    "y": s.y if s.y is not None else "",
                    "z": s.z if s.z is not None else "",
                    "category": s.category,
                    "region": s.region or "",
                    "faction": s.faction or "",
                    "notes": s.notes or "",
                }
            )


def append_jump_event(path: Path, event: JumpEvent) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "timestamp_utc": event.timestamp_utc,
        "origin": event.origin,
        "destination": event.destination,
        "origin_coords": event.origin_coords,
        "destination_coords": event.destination_coords,
        "cargo": event.cargo,
        "ship": event.ship,
        "fsd_type": event.fsd_type,
        "notes": event.notes,
        "anomaly_visual": event.anomaly_visual,
        "anomaly_audio": event.anomaly_audio,
        "anomaly_duration": event.anomaly_duration,
        "extra": event.extra,
    }
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(data) + "\n")


def load_jump_events(path: Path) -> List[JumpEvent]:
    events: List[JumpEvent] = []
    if not path.exists():
        return events

    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            obj = json.loads(line)
            events.append(
                JumpEvent(
                    timestamp_utc=obj["timestamp_utc"],
                    origin=obj["origin"],
                    destination=obj["destination"],
                    origin_coords=tuple(obj["origin_coords"]) if obj.get("origin_coords") else None,
                    destination_coords=tuple(obj["destination_coords"]) if obj.get("destination_coords") else None,
                    cargo=obj.get("cargo"),
                    ship=obj.get("ship"),
                    fsd_type=obj.get("fsd_type"),
                    notes=obj.get("notes"),
                    anomaly_visual=obj.get("anomaly_visual", False),
                    anomaly_audio=obj.get("anomaly_audio", False),
                    anomaly_duration=obj.get("anomaly_duration", False),
                    extra=obj.get("extra"),
                )
            )
    return events


def load_lore_file(path: Path, identifier: str, title: str, source: str) -> LoreText:
    with path.open("r", encoding="utf-8") as f:
        body = f.read()
    return LoreText(identifier=identifier, title=title, source=source, body=body)
