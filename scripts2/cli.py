from __future__ import annotations
import argparse
import sys
from pathlib import Path
from typing import List

from .config import (
    SYSTEMS_CSV,
    GUARDIAN_SYSTEMS_CSV,
    LORE_DIR,
    WITCHSPACE_LOG,
    OMPHALOS_VIZ_JSON,
    GUARDIAN_VIZ_JSON,
)
from .data_io import load_systems_csv, write_systems_csv, load_lore_file
from .geometry import (
    compute_all_pair_distances,
    group_repeated_distances,
    find_colinear_triplets,
    find_radial_spokes,
)
from .lore_analysis import report_basic_lore_analysis
from .witchspace_log import log_jump, load_all_jumps
from .viz_export import export_systems_to_json
from .models import SystemNode


# ---------- Commands ----------

def cmd_init_omphalos(args: argparse.Namespace) -> None:
    """Create starter omphalos_systems.csv with key Raxxla / Omphalos suspects."""
    systems: List[SystemNode] = [
        SystemNode(name="Polaris", category="permit_locked", region="Frontier_Legacy", faction=None,
                   notes="Classic Thargoid staging / transport lore. Fill in coords."),
        SystemNode(name="Shinrarta Dezhra", category="lore_hub", region="Core", faction="The Dark Wheel",
                   notes="Jameson Memorial, Dark Wheel faction base."),
        SystemNode(name="LFT 509", category="permit_locked", region="Bubble Fringe", faction=None,
                   notes="Gas giant with 8th moon in lore."),
        SystemNode(name="Col 285 Sector BG-O d6-93", category="anomaly", region="Col 285",
                   notes="Delta 69 comms anomaly; phantom mass & ghost signal."),
        SystemNode(name="Nefertem", category="ghost_ship", region="Bubble Fringe",
                   notes="Generation Ship Thetis & insanity signal."),
        SystemNode(name="Syreadiae JX-F c0", category="megaship", region="Formidine Rift",
                   notes="Zurara; Project Dynasty."),
        SystemNode(name="HIP 22460", category="battlefield", region="Pleiades Fringe",
                   notes="Proteus Wave site; Guardian+Thargoid catastrophe."),
        SystemNode(name="HIP 87621", category="permit_locked", region="Bubble Fringe",
                   notes="October Consortium system; Terri Tora mystery."),
        SystemNode(name="Sol", category="reference", region="Core",
                   notes="Reference origin system (0,0,0 if using Sol-centric coords)."),
    ]
    write_systems_csv(SYSTEMS_CSV, systems)
    print(f"Initialized Omphalos systems CSV at {SYSTEMS_CSV}")


def cmd_init_guardian(args: argparse.Namespace) -> None:
    """Create a stub guardian_systems.csv you can replace with your existing Guardian Hunt export."""
    systems: List[SystemNode] = [
        SystemNode(name="Guardian_Shell_Center", category="guardian_shell", region="Guardian_Shell",
                   notes="Default Guardian shell center; customise this or replace with your real shell / hotspot data."),
    ]
    write_systems_csv(GUARDIAN_SYSTEMS_CSV, systems)
    print(f"Initialized Guardian systems CSV at {GUARDIAN_SYSTEMS_CSV}")


def cmd_geometry(args: argparse.Namespace) -> None:
    """Analyze geometric patterns in a given systems CSV."""
    csv_path: Path = args.csv if args.csv else SYSTEMS_CSV
    systems = load_systems_csv(csv_path)
    print(f"Loaded {len(systems)} systems from {csv_path}")

    distances = compute_all_pair_distances(systems)
    repeats = group_repeated_distances(distances)
    print("\n== Repeated distances (approx, may hint at geometric patterns) ==")
    if not repeats:
        print("No repeated distances above threshold.")
    else:
        for d, pairs in sorted(repeats.items(), key=lambda kv: kv[0]):
            print(f"{d:.3f} ly: {pairs}")

    triplets = find_colinear_triplets(systems)
    print("\n== Nearly colinear triplets (possible 'lines' / 'rays') ==")
    if not triplets:
        print("No colinear triplets found.")
    else:
        for a, b, c in triplets:
            print(f"{a.name} - {b.name} - {c.name}")

    if args.center:
        try:
            spokes = find_radial_spokes(systems, args.center, args.angle)
        except ValueError as e:
            print(f"Error: {e}")
            return
        print(f"\n== Radial spokes from {args.center} (<= {args.angle}° apart) ==")
        if not spokes:
            print("No notable spokes found.")
        else:
            for s1, s2 in spokes:
                print(f"{args.center} -> {s1.name} & {s2.name}")


def cmd_lore(args: argparse.Namespace) -> None:
    path = LORE_DIR / args.file
    lore = load_lore_file(
        path,
        identifier=args.identifier or args.file,
        title=args.title or args.file,
        source=args.source or "unknown",
    )
    report = report_basic_lore_analysis(lore)
    print("== Lore analysis report ==")
    for k, v in report.items():
        print(f"{k}: {v}")


def cmd_log_jump(args: argparse.Namespace) -> None:
    cargo = args.cargo.split(",") if args.cargo else None
    log_jump(
        origin=args.origin,
        destination=args.destination,
        cargo=[c.strip() for c in cargo] if cargo else None,
        ship=args.ship,
        fsd_type=args.fsd,
        notes=args.notes,
        anomaly_visual=args.visual,
        anomaly_audio=args.audio,
        anomaly_duration=args.duration,
    )
    print(f"Logged jump {args.origin} -> {args.destination} to {WITCHSPACE_LOG}")


def cmd_report_jumps(args: argparse.Namespace) -> None:
    events = load_all_jumps()
    print(f"Loaded {len(events)} jump events from {WITCHSPACE_LOG}")
    anomaly_count = 0
    for e in events:
        if e.anomaly_visual or e.anomaly_audio or e.anomaly_duration:
            anomaly_count += 1
    print(f"Total anomaly-flagged jumps: {anomaly_count}")

    if args.verbose:
        for e in events:
            if e.anomaly_visual or e.anomaly_audio or e.anomaly_duration:
                print("-" * 40)
                print(f"{e.timestamp_utc}: {e.origin} -> {e.destination}")
                print(f"  cargo: {e.cargo}")
                print(f"  anomalies: visual={e.anomaly_visual}, audio={e.anomaly_audio}, duration={e.anomaly_duration}")
                if e.notes:
                    print(f"  notes: {e.notes}")


def _export_generic(csv_path: Path, out_path: Path, center: str | None, k: int, layer_name: str) -> None:
    systems = load_systems_csv(csv_path)
    if not systems:
        print(f"No systems loaded from {csv_path}")
        return

    meta = {
        "center": center,
        "k_neighbors": k,
        "layer": layer_name,
    }

    export_systems_to_json(
        systems=systems,
        path=out_path,
        add_links=True,
        k_neighbors=k,
        meta=meta,
    )


def cmd_export_viz_omphalos(args: argparse.Namespace) -> None:
    csv_path = SYSTEMS_CSV
    out_path: Path = args.out if args.out else OMPHALOS_VIZ_JSON
    _export_generic(csv_path, out_path, args.center, args.k, "omphalos")


def cmd_export_viz_guardian(args: argparse.Namespace) -> None:
    csv_path = GUARDIAN_SYSTEMS_CSV
    out_path: Path = args.out if args.out else GUARDIAN_VIZ_JSON
    _export_generic(csv_path, out_path, args.center, args.k, "guardian")


# ---------- Parser / main ----------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="omphalos_hunt",
        description="Unified Omphalos / Guardian Hunt Toolkit CLI",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    # Init CSVs
    p_init_o = sub.add_parser("init-omphalos", help="Create starter omphalos_systems.csv")
    p_init_o.set_defaults(func=cmd_init_omphalos)

    p_init_g = sub.add_parser("init-guardian", help="Create stub guardian_systems.csv")
    p_init_g.set_defaults(func=cmd_init_guardian)

    # Geometry
    p_geom = sub.add_parser("geometry", help="Analyze geometric patterns in a systems CSV")
    p_geom.add_argument("--csv", type=Path, help="Path to systems CSV (default: omphalos_systems.csv)")
    p_geom.add_argument("--center", type=str, help="Name of center system for radial spoke analysis")
    p_geom.add_argument("--angle", type=float, default=1.0, help="Angle tolerance in degrees")
    p_geom.set_defaults(func=cmd_geometry)

    # Lore
    p_lore = sub.add_parser("lore", help="Run basic lore/cipher analysis on a text file in data/lore_samples")
    p_lore.add_argument("file", type=str, help="Filename under data/lore_samples (e.g. dark_wheel_toast.txt)")
    p_lore.add_argument("--identifier", type=str, default=None)
    p_lore.add_argument("--title", type=str, default=None)
    p_lore.add_argument("--source", type=str, default=None)
    p_lore.set_defaults(func=cmd_lore)

    # Witch-space logs
    p_log = sub.add_parser("log-jump", help="Append a witch-space jump event to the log")
    p_log.add_argument("origin", type=str)
    p_log.add_argument("destination", type=str)
    p_log.add_argument("--cargo", type=str, default="", help="Comma-separated cargo items")
    p_log.add_argument("--ship", type=str, default=None)
    p_log.add_argument("--fsd", type=str, default=None, help="FSD / booster description")
    p_log.add_argument("--notes", type=str, default=None)
    p_log.add_argument("--visual", action="store_true", help="Flag visual anomaly")
    p_log.add_argument("--audio", action="store_true", help="Flag audio anomaly")
    p_log.add_argument("--duration", action="store_true", help="Flag duration/time anomaly")
    p_log.set_defaults(func=cmd_log_jump)

    p_rep = sub.add_parser("report-jumps", help="Summarize anomaly patterns in logged jumps")
    p_rep.add_argument("--verbose", action="store_true")
    p_rep.set_defaults(func=cmd_report_jumps)

    # Visualization exports
    p_viz_o = sub.add_parser("export-viz-omphalos", help="Export Omphalos systems to JSON for 3D visualization")
    p_viz_o.add_argument(
        "--out",
        type=Path,
        default=None,
        help=f"Output JSON path (default: {OMPHALOS_VIZ_JSON})",
    )
    p_viz_o.add_argument(
        "--k",
        type=int,
        default=3,
        help="Number of nearest neighbors per node for link generation",
    )
    p_viz_o.add_argument(
        "--center",
        type=str,
        default=None,
        help="Optional center system name to record in meta.",
    )
    p_viz_o.set_defaults(func=cmd_export_viz_omphalos)

    p_viz_g = sub.add_parser("export-viz-guardian", help="Export Guardian systems to JSON for 3D visualization")
    p_viz_g.add_argument(
        "--out",
        type=Path,
        default=None,
        help=f"Output JSON path (default: {GUARDIAN_VIZ_JSON})",
    )
    p_viz_g.add_argument(
        "--k",
        type=int,
        default=3,
        help="Number of nearest neighbors per node for link generation",
    )
    p_viz_g.add_argument(
        "--center",
        type=str,
        default=None,
        help="Optional center system name to record in meta.",
    )
    p_viz_g.set_defaults(func=cmd_export_viz_guardian)

    return parser


def main(argv: List[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main(sys.argv[1:])
