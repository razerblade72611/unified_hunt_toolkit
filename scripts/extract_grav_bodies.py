import argparse
import csv
from edsm_stream import iter_json_array_objects_gz

INTEREST = {
    "Black Hole",
    "Neutron Star",
    "White Dwarf",
}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--path", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    rows = []
    for sysobj in iter_json_array_objects_gz(args.path):
        system = sysobj.get("systemName") or sysobj.get("name")
        for body in (sysobj.get("bodies") or []):
            if body.get("type") != "Star":
                continue
            sub = body.get("subType") or ""
            if sub in INTEREST:
                rows.append({
                    "system": system,
                    "bodyName": body.get("name"),
                    "subType": sub,
                    "spectralClass": body.get("spectralClass"),
                    "isMainStar": body.get("isMainStar"),
                })

    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["system","bodyName","subType","spectralClass","isMainStar"])
        w.writeheader()
        w.writerows(rows)

    print(f"Wrote {len(rows)} rows -> {args.out}")

if __name__ == "__main__":
    main()
