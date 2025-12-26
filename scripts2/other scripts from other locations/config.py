# config.py

from pathlib import Path

# Base directories
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"

EDSM_RAW_DIR = RAW_DIR / "edsm"
EDASTRO_RAW_DIR = RAW_DIR / "edastro"
CANONN_RAW_DIR = RAW_DIR / "canonn"

# --- Remote URLs ---

# EDSM nightly dumps (official)
EDSM_URLS = {
    "systemsWithCoordinates.json.gz": "https://www.edsm.net/dump/systemsWithCoordinates.json.gz",
    "systemsWithCoordinates7days.json.gz": "https://www.edsm.net/dump/systemsWithCoordinates7days.json.gz",
}

# EDastro spreadsheets (POIs + nebulae + region key + catalog systems)
EDASTRO_URLS = {
    # Combined POI sources (EDSM, GMP, DSSA, IGAU)
    "points_of_interest.csv": "https://edastro.b-cdn.net/mapcharts/files/edsmPOI.csv",
    # Nebulae coordinates
    "nebulae_coordinates.csv": "https://edastro.b-cdn.net/mapcharts/files/nebulae-coordinates.csv",
    # Region ID / Name key
    "regionID.csv": "https://edastro.b-cdn.net/mapcharts/files/regionID.csv",
    # Catalog Systems (non-procedural names)
    "catalog_systems.csv": "https://edastro.b-cdn.net/mapcharts/files/systems-nonproc.csv",
}

# Canonn dumps (codex, FSS, signals, + Google Sheets)
CANONN_URLS = {
    # JSON dumps
    "codex.json.gz": "https://canonn.fyi/codex.json.gz",
    "fss.json.gz": "https://canonn.fyi/fss.json.gz",
    "signals.json.gz": "https://canonn.fyi/signals.json.gz",

    # The following four are Google Sheets export links.
    # Right now they're placeholders so the script still runs.
    # When you're ready, replace each value with the real
    # `.../export?format=csv` URL from the corresponding sheet.
    "surface_biology.csv": "PLACEHOLDER_SURFACE_BIOLOGY_URL",
    "lagrange_cloud.csv": "PLACEHOLDER_LAGRANGE_CLOUD_URL",
    "guardian_codex.csv": "PLACEHOLDER_GUARDIAN_CODEX_URL",
    "thargoid_codex.csv": "PLACEHOLDER_THARGOID_CODEX_URL",
}

# --- Omphalos geometry parameters ---

# How far from Sol we keep generic systems (you can change this)
MAX_RADIUS_LY = 2000.0

# Systems to always keep even if outside radius (or if filters miss them)
ALWAYS_KEEP_SYSTEMS = {
    "Sol",
    "Shinrarta Dezhra",
    "LFT 509",
    "Polaris",
    "Robigo",
    "HIP 87621",
    "HIP 22460",
    "Maia",
}
