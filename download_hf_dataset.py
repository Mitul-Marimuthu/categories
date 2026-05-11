#!/usr/bin/env python3
"""Download jaypasnagasai/magpie from HuggingFace and save as JSON."""

import json
import urllib.request
from pathlib import Path

DATASET = "jaypasnagasai/magpie"
OUTPUT = Path("scenarios/magpie_hf.json")
API_BASE = "https://datasets-server.huggingface.co"
BATCH = 100  # max rows per request


def get_splits() -> list[str]:
    url = f"{API_BASE}/splits?dataset={DATASET.replace('/', '%2F')}"
    with urllib.request.urlopen(url) as r:
        data = json.loads(r.read())
    return [s["split"] for s in data.get("splits", [])]


def fetch_rows(split: str, offset: int, length: int) -> dict:
    url = (
        f"{API_BASE}/rows"
        f"?dataset={DATASET.replace('/', '%2F')}"
        f"&config=default&split={split}"
        f"&offset={offset}&length={length}"
    )
    with urllib.request.urlopen(url) as r:
        return json.loads(r.read())


def download_split(split: str) -> list[dict]:
    print(f"  Fetching first batch to get total count...")
    first = fetch_rows(split, 0, BATCH)
    total = first["num_rows_total"]
    rows = [item["row"] for item in first["rows"]]
    print(f"  {total} rows total")

    offset = BATCH
    while offset < total:
        batch = fetch_rows(split, offset, BATCH)
        rows.extend(item["row"] for item in batch["rows"])
        print(f"  {min(offset + BATCH, total)}/{total}", end="\r")
        offset += BATCH

    print(f"  {total}/{total} — done")
    return rows


def main():
    splits = get_splits()
    print(f"Splits found: {splits}\n")

    all_data: dict[str, list] = {}
    for split in splits:
        print(f"Downloading split: {split}")
        all_data[split] = download_split(split)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT, "w") as f:
        json.dump(all_data, f, indent=2)

    total = sum(len(v) for v in all_data.values())
    print(f"\nSaved {total} rows to {OUTPUT}")


if __name__ == "__main__":
    main()
