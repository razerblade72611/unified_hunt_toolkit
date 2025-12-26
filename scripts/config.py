"""Configuration for Omphalos / Raxxla hunt data pipeline.

This module assumes the following repo layout (relative to this file):

    PROJECT_ROOT/
      data/
        raw/
          edsm/
            systemsWithCoordinates.json.gz
          edastro/
            points_of_interest.csv   (or edsmPOI.csv from EDastro)
          community/
            permit_locked_systems.csv
            lore_hubs.csv
        processed/
            omphalos_systems.csv
            omphalos_poi.csv
            omphalos_map_base.json
            overlay_poi.json
            overlay_permits.json
            overlay_lore_hubs.json
"""

from pathlib import Path

# Base paths
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"

# Raw data folders
RAW_DIR = DATA_DIR / "raw"
EDSM_RAW_DIR = RAW_DIR / "edsm"
EDASTRO_RAW_DIR = RAW_DIR / "edastro"
COMMUNITY_RAW_DIR = RAW_DIR / "community"

# Processed outputs
PROCESSED_DIR = DATA_DIR / "processed"

# Core CSVs
SYSTEMS_CSV = PROCESSED_DIR / "omphalos_systems.csv"
POI_CSV = PROCESSED_DIR / "omphalos_poi.csv"

# Community overlay CSVs (you provide these)
PERMIT_CSV = COMMUNITY_RAW_DIR / "permit_locked_systems.csv"
LORE_HUBS_CSV = COMMUNITY_RAW_DIR / "lore_hubs.csv"

# JSON outputs for viewer
MAP_BASE_JSON = PROCESSED_DIR / "omphalos_map_base.json"
OVERLAY_POI_JSON = PROCESSED_DIR / "overlay_poi.json"
OVERLAY_PERMITS_JSON = PROCESSED_DIR / "overlay_permits.json"
OVERLAY_LORE_HUBS_JSON = PROCESSED_DIR / "overlay_lore_hubs.json"
