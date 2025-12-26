Unified Hunt Toolkit – Omphalos / Operation Orpheus Companion
==============================================================

This project has been extended with:

* `omphalos_hunt.harvest` – data harvesters for EDSM system coordinates,
  Elite: Dangerous journal files (witch-space jump log), and lore indexing.
* `omphalos_hunt.scoring` – Raxxla Likelihood Index (RLI) scoring combining
  geometry, lore connections, and logged anomalies.
* `web/server.py` – a minimal Flask web console providing a table of RLI
  scores and buttons to trigger harvesters.
* `run_server.py` – convenience entrypoint for the web console.

Quick start
-----------

1. Create and activate a Python virtualenv.
2. Install requirements:

   pip install -r requirements.txt

3. Run the web console from the project root:

   python run_server.py

4. Open the URL printed by Flask (usually http://127.0.0.1:5000/) in your browser.

5. Use the buttons to:
   * Harvest EDSM coordinates (fills in missing x/y/z for systems in
     `data/omphalos_systems.csv`).
   * Import journals (you must provide the path in a JSON body when calling
     the API from another tool, or extend the server to hard-code your path).
   * Index lore (analyses text files in `data/lore_samples`).
   * Refresh scores (recomputes the RLI using geometry + lore + anomalies).

CLI usage
---------

The original CLI entrypoints remain in `omphalos_hunt.cli`. You can continue
to use them, and you may also import the new modules directly, for example:

    from omphalos_hunt.harvest import fill_missing_coords_from_edsm
    from omphalos_hunt.scoring import score_systems_as_dict

Notes
-----

* All external integrations (EDSM, journals) run locally from your machine.
* No network access is required except for EDSM queries, which you can
  disable by not calling the harvester.
* This README was added by ChatGPT to document the additional modules.
