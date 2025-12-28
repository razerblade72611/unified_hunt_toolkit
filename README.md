Unified Hunt Toolkit (Elite Dangerous)

A local, data-driven toolkit for exploring and visualizing Elite Dangerous hunt hypotheses in 3D:

Omphalos map (system point cloud + POIs)

Guardian shell / hotspots

Sky “anchor vectors”

Gravity warp visualization (local + optimized global slice)

This repo is designed to run locally and render interactive 3D maps in your browser.

## Demo video

[![Watch the demo](https://img.youtube.com/vi/JStHuUX0ZW4/hqdefault.jpg)](https://www.youtube.com/watch?v=JStHuUX0ZW4)


What you get
Web viewer(s)

Interactive Three.js maps located in /web/, for example:

web/unified_map12.5.html (corridors + optimized warp + source selection)

Data inputs / outputs

This project expects JSON data in:

data/processed/

Common processed files:

guardian_map.json

omphalos_map.json

sky_ed.json

gravity_sources.json or gravity_sources_full.json (preferred if present)

Note: Many projects keep large processed data out of git history. If a file is missing, generate it (recommended) or download it from a Release/asset if you publish one.

Requirements

Windows 10/11 (works on other OS too)

Python 3.10+ recommended

Git

A modern browser (Chrome / Edge recommended)

Quickstart (run the map)
1) Clone the repo
git clone https://github.com/razerblade72611/unified_hunt_toolkit.git
cd unified_hunt_toolkit

2) Create & activate a virtual environment (recommended)
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip

3) Install dependencies (optional but recommended)

If you have a requirements.txt:

pip install -r requirements.txt


If you don’t have one yet, you can still run the web viewer (it only needs static JSON), but you’ll need dependencies to run the data-build scripts later.

4) Start a local web server (from repo root)

Run this in the folder that contains /web and /data:

python -m http.server 8000

5) Open the viewer

In your browser:

http://localhost:8000/web/unified_map12.5.html

Data setup

The viewer loads JSON from data/processed/ using relative paths.
If the map loads but layers are missing, it usually means a JSON file is missing or the paths don’t match.

Expected paths (default)

The viewer typically loads:

data/processed/guardian_map.json

data/processed/omphalos_map.json

data/processed/sky_ed.json

data/processed/gravity_sources_full.json (preferred)

fallback: data/processed/gravity_sources.json

If processed files are missing
Option A — Generate them locally (recommended)

Run your pipeline scripts (names vary by repo — use what exists in /scripts):

ls .\scripts


Example commands (adjust to match your script names):

python -m scripts.build_omphalos_poi
python -m scripts.build_omphalos_map_json
python -m scripts.build_gravity_sources

Option B — Download prebuilt processed data

If you publish large processed JSON as GitHub Release assets, download them into:

data/processed/

Using the viewer
Layers

Guardian Shell / Hotspots: toggles Guardian layer

Omphalos: point cloud systems

Sky: anchor vectors / rays

Corridor tool

Choose a Sky vector

Set corridor length & radius

Click Rebuild Corridor

Points inside the corridor highlight in the Omphalos layer

Gravity warp

Local warp: focused detail (manual selection or “Focus System”)

Global warp: optimized slice across the whole region

Auto Global Sources: voxel-capped auto-selection for performance

Troubleshooting
“It loads but nothing shows”

Confirm you are serving from the repo root (must contain /web and /data)

Hard refresh: Ctrl+Shift+R

Open DevTools Console (F12) and look for HTTP 404 or JSON schema errors

“Global warp is slow”

Use Slice mode (XY/XZ/YZ) instead of Cube

Try built-in presets (Balanced / Ultra / Texture)

Increase voxel size or reduce K (auto global sources)

Reduce global divisions or steps

“Line colors / contrast breaks sometimes”

If you added “deviation highlight” logic, the most common failure is invalid color values.

Safe rules:

Clamp opacity to [0..1]

Ensure all THREE.Color inputs are valid (hex string like #RRGGBB or numeric)

Avoid per-segment material swapping; prefer:

vertex colors, or

a second overlay LineSegments for “deviating” segments

Project structure (typical)

web/ — Three.js viewers

data/raw/ — large/raw dumps (often not committed)

data/processed/ — JSON outputs consumed by the viewers

scripts/ — build/ingest/transform pipeline utilities

License

TBD (add your preferred license here).
