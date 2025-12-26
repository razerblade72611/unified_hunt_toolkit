# scripts/download_raw_data.py

import gzip
import sys
from pathlib import Path

import requests
from tqdm import tqdm

# Import config paths and URLs
sys.path.append(str(Path(__file__).resolve().parents[1]))
from config import (
    EDSM_RAW_DIR,
    EDASTRO_RAW_DIR,
    CANONN_RAW_DIR,
    EDSM_URLS,
    EDASTRO_URLS,
    CANONN_URLS,
)

def ensure_dirs():
    for d in (EDSM_RAW_DIR, EDASTRO_RAW_DIR, CANONN_RAW_DIR):
        d.mkdir(parents=True, exist_ok=True)


def download_file(url: str, dest: Path, chunk_size: int = 8192) -> None:
    """
    Stream-download a file with a progress bar.
    If the file already exists, skip by default.
    """
    if dest.exists():
        print(f"[SKIP] {dest} already exists")
        return

    print(f"[DL] {url} -> {dest}")
    dest.parent.mkdir(parents=True, exist_ok=True)

    with requests.get(url, stream=True, timeout=60) as r:
        r.raise_for_status()
        total = int(r.headers.get("content-length", 0))
        progress = tqdm(
            total=total,
            unit="B",
            unit_scale=True,
            unit_divisor=1024,
            desc=dest.name,
        )
        with open(dest, "wb") as f:
            for chunk in r.iter_content(chunk_size=chunk_size):
                if chunk:
                    f.write(chunk)
                    progress.update(len(chunk))
        progress.close()


def download_edsm():
    print("\n=== Downloading EDSM nightly dumps ===")
    for filename, url in EDSM_URLS.items():
        dest = EDSM_RAW_DIR / filename
        download_file(url, dest)


def download_edastro():
    print("\n=== Downloading EDastro CSVs ===")
    for filename, url in EDASTRO_URLS.items():
        dest = EDASTRO_RAW_DIR / filename
        download_file(url, dest)


def download_canonn():
    print("\n=== Downloading Canonn dumps ===")
    for filename, url in CANONN_URLS.items():
        # Skip placeholder Google Sheets URLs that still have 'Id' in them
        if "Id/export" in url:
            print(f"[WARN] Placeholder URL for {filename}; please update in config.py")
            continue
        dest = CANONN_RAW_DIR / filename
        download_file(url, dest)


def main():
    ensure_dirs()
    download_edsm()
    download_edastro()
    download_canonn()
    print("\nDone. Raw data in ./data/raw/")


if __name__ == "__main__":
    main()
