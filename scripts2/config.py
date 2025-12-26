from pathlib import Path

# Base paths
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"

# Omphalos / Raxxla systems
SYSTEMS_CSV = DATA_DIR / "omphalos_systems.csv"

# Guardian frontier / shell systems (you can hook this to your existing Guardian pipeline)
GUARDIAN_SYSTEMS_CSV = DATA_DIR / "guardian_systems.csv"

# Lore directory
LORE_DIR = DATA_DIR / "lore_samples"

# Witch-space jump log
WITCHSPACE_LOG = DATA_DIR / "witchspace_jumps.jsonl"

# Visualization JSON outputs
OMPHALOS_VIZ_JSON = DATA_DIR / "omphalos_map.json"
GUARDIAN_VIZ_JSON = DATA_DIR / "guardian_map.json"

# Numerical tolerances for geometry
DISTANCE_EPSILON = 0.01   # ly, for "equal distance" comparisons
COLINEAR_EPSILON = 0.001  # for area-based colinearity checks
