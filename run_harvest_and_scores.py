from pathlib import Path

from omphalos_hunt.config import SYSTEMS_CSV
from omphalos_hunt.harvest import (
    fill_missing_coords_from_edsm,
    import_journals_to_witchspace,
    index_lore_directory,
)
from omphalos_hunt.scoring import score_systems_as_dict

print("=== Harvest: EDSM coordinates ===")
updated = fill_missing_coords_from_edsm(SYSTEMS_CSV, dry_run=False)
print(f"Updated coordinates for {updated} systems.")

print("\n=== Harvest: Lore index ===")
indexed = index_lore_directory()
print(f"Indexed {indexed} lore files.")

print("\n=== Harvest: Journals -> witchspace log ===")
journal_dir = Path(r"C:\Users\davei\Saved Games\Frontier Developments\Elite Dangerous")
print(f"Using journal directory: {journal_dir}")
if journal_dir.exists():
    count = import_journals_to_witchspace(journal_dir, cmdr_hint=None, dry_run=False)
    print(f"Imported {count} jumps from journals.")
else:
    print(f"WARNING: Journal directory not found: {journal_dir}")

print("\n=== Raxxla Likelihood Index (RLI) ===")
scores = score_systems_as_dict()
top = sorted(scores.items(), key=lambda kv: kv[1]["rli"], reverse=True)

for name, s in top:
    print(f"{name:25} RLI={s['rli']:.1f}  geom={s['geometry']:.3f}  lore={s['lore']:.3f}  anom={s['anomalies']:.3f}")
