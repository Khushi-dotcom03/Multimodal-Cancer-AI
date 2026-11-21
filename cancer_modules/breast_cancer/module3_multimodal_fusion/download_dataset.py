"""Download the official BrEaST/TCIA files without overwriting local data."""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import time

import requests


DATA_DIR = Path(__file__).resolve().parent / "data"
RAW_DIR = DATA_DIR / "raw"
OFFICIAL_FILES = {
    "BrEaST-Lesions_USG-images_and_masks-Dec-15-2023.zip": (
        "https://www.cancerimagingarchive.net/wp-content/uploads/"
        "BrEaST-Lesions_USG-images_and_masks-Dec-15-2023.zip"
    ),
    "BrEaST-Lesions-USG-clinical-data-Dec-15-2023.xlsx": (
        "https://www.cancerimagingarchive.net/wp-content/uploads/"
        "BrEaST-Lesions-USG-clinical-data-Dec-15-2023.xlsx"
    ),
}


def download_file(url: str, destination: Path, *, chunk_size: int = 2 * 1024 * 1024) -> None:
    """Fetch a TCIA file with byte-range resume and strict no-overwrite behavior."""
    if destination.exists():
        raise FileExistsError(f"Refusing to overwrite existing file: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_name(destination.name + ".part")
    session = requests.Session()

    head = session.get(url, headers={"Range": "bytes=0-0"}, stream=True, timeout=(20, 60))
    head.raise_for_status()
    content_range = head.headers.get("Content-Range", "")
    match = re.fullmatch(r"bytes 0-0/(\d+)", content_range)
    head.close()
    if not match:
        raise RuntimeError(f"TCIA server did not provide a valid byte range for {url}")
    total_size = int(match.group(1))

    offset = partial.stat().st_size if partial.exists() else 0
    if offset > total_size:
        raise RuntimeError(f"Partial file is larger than source ({offset}>{total_size}): {partial}")
    if offset == 0 and partial.exists():
        partial.unlink()

    with partial.open("ab") as output:
        while offset < total_size:
            end = min(offset + chunk_size - 1, total_size - 1)
            for attempt in range(4):
                try:
                    response = session.get(
                        url,
                        headers={"Range": f"bytes={offset}-{end}"},
                        stream=True,
                        timeout=(20, 120),
                    )
                    response.raise_for_status()
                    expected_range = f"bytes {offset}-{end}/{total_size}"
                    if response.status_code != 206 or response.headers.get("Content-Range") != expected_range:
                        raise RuntimeError(
                            f"Unexpected range response for {destination.name}: "
                            f"{response.status_code}, {response.headers.get('Content-Range')}"
                        )
                    block = b"".join(response.iter_content(256 * 1024))
                    response.close()
                    expected_length = end - offset + 1
                    if len(block) != expected_length:
                        raise RuntimeError(f"Short download block ({len(block)}!={expected_length})")
                    output.write(block)
                    output.flush()
                    offset += len(block)
                    print(f"{destination.name}: {offset}/{total_size}", flush=True)
                    break
                except Exception:
                    if attempt == 3:
                        raise
                    time.sleep(attempt + 1)

    if partial.stat().st_size != total_size:
        raise RuntimeError(f"Download size mismatch for {destination}: {partial.stat().st_size}/{total_size}")
    partial.replace(destination)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", type=Path, default=RAW_DIR)
    args = parser.parse_args()
    for filename, url in OFFICIAL_FILES.items():
        download_file(url, args.raw_dir / filename)


if __name__ == "__main__":
    main()
