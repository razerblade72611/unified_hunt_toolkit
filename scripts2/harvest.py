
from __future__ import annotations

"""
Harvesters for bringing external data into the Omphalos / Raxxla toolkit.

This module is intentionally self-contained and has no incomplete stubs:
all functions are usable as-is, and can be imported from CLI, notebooks,
or the web GUI.
"""

import json
import logging
from pathlib import Path
from typing import Optional, Tuple, List, Dict, Any

import requests

from .config import SYSTEMS_CSV, DATA_DIR, LORE_DIR, WITCHSPACE_LOG
from .data_io import (
    load_systems_csv,
    write_systems_csv,
    load_jump_events,
    append_jump_event,
    load_lore_file,
)
from .models import SystemNode, JumpEvent, LoreText
from .lore_analysis import report_basic_lore_analysis

log = logging.getLogger(__name__)

EDSM_BASE = "https://www.edsm.net/api-v1"


# ---------------------------------------------------------------------------
# EDSM system coordinate harvest
# ---------------------------------------------------------------------------

def _edsm_get_system(name: str) -> Optional[Dict[str, Any]]:
    """Query EDSM for a single system, returning JSON if coordinates exist.

    Returns None if the system is not known or has no coordinates recorded.
    """
    params = {
        "systemName": name,
        "showCoordinates": 1,
        "showPermit": 1,
    }
    try:
        resp = requests.get(f"{EDSM_BASE}/system", params=params, timeout=10)
    except Exception as exc:  # network / DNS / etc
        log.warning("EDSM request failed for %s: %s", name, exc)
        return None

    if resp.status_code != 200:
        log.warning("EDSM returned status %s for %s", resp.status_code, name)
        return None

    try:
        data = resp.json()
    except Exception as exc:
        log.warning("EDSM JSON decode failed for %s: %s", name, exc)
        return None

    if not data or "coords" not in data:
        return None
    return data


def fill_missing_coords_from_edsm(
    csv_path: Path = SYSTEMS_CSV,
    dry_run: bool = False,
) -> int:
    """Fill in missing x/y/z coordinates for systems listed in *csv_path*.

    Systems are looked up on EDSM by name. When coordinates are found, the
    SystemNode is updated. If *dry_run* is True, changes are not written
    back to disk but the number of updatable systems is still returned.
    """
    systems = load_systems_csv(csv_path)
    updated = 0

    for s in systems:
        if s.x is not None and s.y is not None and s.z is not None:
            continue

        data = _edsm_get_system(s.name)
        if not data:
            log.info("No EDSM entry for %s", s.name)
            continue

        coords = data.get("coords") or {}
        x, y, z = coords.get("x"), coords.get("y"), coords.get("z")
        if x is None or y is None or z is None:
            log.info("EDSM has no coords for %s (coords=%r)", s.name, coords)
            continue

        s.x, s.y, s.z = float(x), float(y), float(z)
        updated += 1
        log.info("Set coords for %s -> (%.3f, %.3f, %.3f)", s.name, s.x, s.y, s.z)

        # If EDSM reports permit-lock state, record that in notes.
        info = data.get("information") or {}
        if data.get("requirePermit"):
            permit_name = info.get("permitName")
            cat = s.category or ""
            if "permit" not in cat:
                s.category = (cat or "permit_locked")
            note_frag = f"Permit-locked"
            if permit_name:
                note_frag += f" ({permit_name})"
            if s.notes:
                if note_frag not in s.notes:
                    s.notes = s.notes + " " + note_frag
            else:
                s.notes = note_frag

    if not dry_run and updated:
        write_systems_csv(csv_path, systems)

    return updated


# ---------------------------------------------------------------------------
# Journal harvesting -> witch-space jump log
# ---------------------------------------------------------------------------

def _iter_journal_events(journal_file: Path):
    """Yield parsed JSON events from a single Journal*.log file.

    Lines that are not valid JSON are ignored.
    """
    with journal_file.open("r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                evt = json.loads(line)
            except json.JSONDecodeError:
                continue
            yield evt


def _iter_jumps_from_journal(journal_file: Path):
    """Yield (event_json, origin_name, dest_name, origin_pos, dest_pos)."""
    last_system: Optional[str] = None
    last_pos: Optional[List[float]] = None

    for evt in _iter_journal_events(journal_file):
        etype = evt.get("event")
        if etype == "Location":
            last_system = evt.get("StarSystem") or last_system
            last_pos = evt.get("StarPos") or last_pos

        elif etype == "FSDJump":
            dest = evt.get("StarSystem")
            dest_pos = evt.get("StarPos")
            origin = last_system or "(unknown)"
            origin_pos_used = last_pos

            # Update for subsequent jumps
            last_system = dest
            last_pos = dest_pos

            yield evt, origin, dest, origin_pos_used, dest_pos


def _coords_tuple(pos: Optional[List[float]]) -> Optional[Tuple[float, float, float]]:
    if not pos or len(pos) != 3:
        return None
    return float(pos[0]), float(pos[1]), float(pos[2])


def import_journals_to_witchspace(
    journal_dir: Path,
    cmdr_hint: Optional[str] = None,
    dry_run: bool = False,
) -> int:
    """Parse Journal*.log files and append FSDJump entries as JumpEvents.

    Returns the number of JumpEvents appended (or that *would* be appended
    if *dry_run* is True).
    """
    journal_files = sorted(journal_dir.glob("Journal*.log"))
    if not journal_files:
        log.warning("No Journal*.log files found under %s", journal_dir)
        return 0

    appended = 0
    for jf in journal_files:
        log.info("Scanning %s", jf)
        for evt, origin, dest, origin_pos, dest_pos in _iter_jumps_from_journal(jf):
            ts = evt.get("timestamp")
            ship = evt.get("Ship")
            fsd = evt.get("FSDType")
            cmdr = evt.get("Commander") or cmdr_hint
            jump_dist = evt.get("JumpDist")

            event = JumpEvent(
                timestamp_utc=ts,
                origin=origin,
                destination=dest,
                origin_coords=_coords_tuple(origin_pos),
                destination_coords=_coords_tuple(dest_pos),
                cargo=None,
                ship=ship,
                fsd_type=fsd,
                notes=f"imported_from_journal:{jf.name}, cmdr={cmdr}, jump_dist={jump_dist}",
                anomaly_visual=False,
                anomaly_audio=False,
                anomaly_duration=False,
                extra={"raw": evt},
            )
            if not dry_run:
                append_jump_event(WITCHSPACE_LOG, event)
            appended += 1

    return appended


# ---------------------------------------------------------------------------
# Lore indexing
# ---------------------------------------------------------------------------

def index_lore_directory(
    lore_dir: Path = LORE_DIR,
    out_path: Path = DATA_DIR / "lore_features.jsonl",
) -> int:
    """Analyse all *.txt lore files and dump a JSONL feature index.

    Each line in *out_path* is a JSON object with the fields returned by
    report_basic_lore_analysis() plus filename. This file is optional for
    the rest of the toolkit but is useful for debugging and for external
    tooling that wants structured lore features.
    """
    files = sorted(lore_dir.glob("*.txt"))
    if not files:
        log.warning("No lore .txt files found in %s", lore_dir)
        return 0

    out_path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with out_path.open("w", encoding="utf-8") as out:
        for path in files:
            identifier = path.stem
            title = identifier.replace("_", " ").title()
            lore = load_lore_file(path, identifier=identifier, title=title, source="local_file")
            features = report_basic_lore_analysis(lore)
            features["filename"] = path.name
            out.write(json.dumps(features) + "\n")
            count += 1
            log.info("Indexed lore file %s", path.name)

    return count
