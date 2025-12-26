
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict

from flask import Flask, jsonify, request, render_template_string
from apscheduler.schedulers.background import BackgroundScheduler

from omphalos_hunt.harvest import (
    fill_missing_coords_from_edsm,
    import_journals_to_witchspace,
    index_lore_directory,
)
from omphalos_hunt.scoring import score_systems_as_dict
from omphalos_hunt.config import SYSTEMS_CSV

log = logging.getLogger(__name__)

# Very small HTML template – intentionally minimal but functional.
INDEX_HTML = """
<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <title>Unified Hunt Toolkit – Omphalos Console</title>
    <style>
      body { font-family: system-ui, sans-serif; background:#050811; color:#eee; margin:0; padding:1rem; }
      h1 { margin-top:0; }
      button { margin:0.25rem; padding:0.4rem 0.7rem; }
      table { border-collapse: collapse; margin-top:1rem; width:100%; max-width:960px; }
      th, td { border:1px solid #333; padding:0.25rem 0.4rem; font-size:0.9rem; }
      th { background:#111827; }
      tr:nth-child(even) { background:#0b1220; }
      #status { margin-top:0.5rem; font-size:0.85rem; color:#9ca3af; white-space:pre-line; }
    </style>
  </head>
  <body>
    <h1>Unified Hunt Toolkit – Omphalos Console</h1>
    <p>
      This lightweight console complements the Operation Orpheus plotting map.
      Use it to refresh data and inspect the current Raxxla Likelihood Index.
    </p>

    <div>
      <button onclick="doHarvest('coords')">Harvest EDSM coordinates</button>
      <button onclick="doHarvest('journals')">Import journals</button>
      <button onclick="doHarvest('lore')">Index lore</button>
      <button onclick="refreshScores()">Refresh scores</button>
    </div>
    <div id="status"></div>

    <table id="scores">
      <thead>
        <tr>
          <th>System</th>
          <th>Geometry</th>
          <th>Lore</th>
          <th>Anomalies</th>
          <th>RLI (0–100)</th>
        </tr>
      </thead>
      <tbody></tbody>
    </table>

    <script>
      function setStatus(msg) {
        document.getElementById('status').textContent = msg;
      }

      async function doHarvest(kind) {
        setStatus("Running " + kind + " harvest…");
        const resp = await fetch("/api/harvest/" + kind, {method:"POST"});
        const data = await resp.json();
        setStatus(data.message || "Done.");
        if (kind !== "lore") {
          refreshScores();
        }
      }

      async function refreshScores() {
        setStatus("Loading scores…");
        const resp = await fetch("/api/scores");
        const data = await resp.json();
        const tbody = document.querySelector("#scores tbody");
        tbody.innerHTML = "";
        data.systems.sort((a, b) => b.rli - a.rli);
        for (const row of data.systems) {
          const tr = document.createElement("tr");
          tr.innerHTML =
            "<td>" + row.name + "</td>" +
            "<td>" + row.geometry.toFixed(3) + "</td>" +
            "<td>" + row.lore.toFixed(3) + "</td>" +
            "<td>" + row.anomalies.toFixed(3) + "</td>" +
            "<td>" + row.rli.toFixed(1) + "</td>";
          tbody.appendChild(tr);
        }
        setStatus("Scores updated.");
      }

      // Initial load
      refreshScores();
    </script>
  </body>
</html>
"""


def create_app() -> Flask:
    app = Flask(__name__)

    # Scheduler for periodic background jobs.
    scheduler = BackgroundScheduler(daemon=True)

    # Start scheduler immediately (Flask 3 no longer has before_first_request)
    if not scheduler.running:
        # Run once a day
        scheduler.add_job(
            lambda: fill_missing_coords_from_edsm(SYSTEMS_CSV, dry_run=False),
            "interval",
            days=1,
            id="coords",
            replace_existing=True,
        )
        # Run lore index daily
        scheduler.add_job(
            index_lore_directory,
            "interval",
            days=1,
            id="lore",
            replace_existing=True,
        )
        scheduler.start()
        log.info("BackgroundScheduler started.")


    @app.route("/")
    def index() -> str:
        return render_template_string(INDEX_HTML)

    @app.route("/api/harvest/coords", methods=["POST"])
    def api_h_coords():
        updated = fill_missing_coords_from_edsm(SYSTEMS_CSV, dry_run=False)
        return jsonify({"ok": True, "message": f"Updated coordinates for {updated} systems."})

    @app.route("/api/harvest/journals", methods=["POST"])
    def api_h_journals():
        # Journal path must be supplied by user per-call for safety.
        payload: Dict[str, Any] = request.get_json(silent=True) or {}
        journal_dir_raw = payload.get("journal_dir")
        if not journal_dir_raw:
            return jsonify({
                "ok": False,
                "message": "journal_dir not supplied; call with JSON {\"journal_dir\": \"path/to/Journal\"}.",
            }), 400
        journal_dir = Path(journal_dir_raw).expanduser()
        if not journal_dir.exists():
            return jsonify({"ok": False, "message": f"Journal dir not found: {journal_dir}"}), 400
        count = import_journals_to_witchspace(journal_dir, cmdr_hint=None, dry_run=False)
        return jsonify({"ok": True, "message": f"Imported {count} jumps from journals."})


    @app.route("/api/harvest/lore", methods=["POST"])
    def api_h_lore():
        count = index_lore_directory()
        return jsonify({"ok": True, "message": f"Indexed {count} lore files."})

    @app.route("/api/scores", methods=["GET"])
    def api_scores():
        scores = score_systems_as_dict()
        systems_rows = [
            {
                "name": name,
                "geometry": v["geometry"],
                "lore": v["lore"],
                "anomalies": v["anomalies"],
                "rli": v["rli"],
            }
            for name, v in scores.items()
        ]
        return jsonify({"systems": systems_rows})

    return app


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    app = create_app()
    app.run(debug=True)
