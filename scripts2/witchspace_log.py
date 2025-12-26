from __future__ import annotations
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from .models import JumpEvent
from .data_io import append_jump_event, load_jump_events
from .config import WITCHSPACE_LOG


def iso_now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def log_jump(
    origin: str,
    destination: str,
    origin_coords: Optional[tuple[float, float, float]] = None,
    destination_coords: Optional[tuple[float, float, float]] = None,
    cargo: Optional[List[str]] = None,
    ship: Optional[str] = None,
    fsd_type: Optional[str] = None,
    notes: Optional[str] = None,
    anomaly_visual: bool = False,
    anomaly_audio: bool = False,
    anomaly_duration: bool = False,
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    event = JumpEvent(
        timestamp_utc=iso_now_utc(),
        origin=origin,
        destination=destination,
        origin_coords=origin_coords,
        destination_coords=destination_coords,
        cargo=cargo,
        ship=ship,
        fsd_type=fsd_type,
        notes=notes,
        anomaly_visual=anomaly_visual,
        anomaly_audio=anomaly_audio,
        anomaly_duration=anomaly_duration,
        extra=extra,
    )
    append_jump_event(WITCHSPACE_LOG, event)


def load_all_jumps():
    return load_jump_events(WITCHSPACE_LOG)
