#!/usr/bin/env python3
"""Download specific folders from gurusha01/magpie on GitHub."""

import json
import sys
import urllib.request
from pathlib import Path

REPO = "gurusha01/magpie"
BRANCH = "main"
FOLDERS = ["data2", "data/data"]
OUTPUT_DIR = Path("magpie_data")


def get_tree() -> dict:
    url = f"https://api.github.com/repos/{REPO}/git/trees/{BRANCH}?recursive=1"
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def download_file(path: str) -> None:
    raw_url = f"https://raw.githubusercontent.com/{REPO}/{BRANCH}/{path}"
    local_path = OUTPUT_DIR / path
    local_path.parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(raw_url, local_path)


def main() -> None:
    print("Fetching repository tree...")
    tree_data = get_tree()

    if tree_data.get("truncated"):
        print("Warning: tree was truncated (large repo). Some files may be missing.")

    files_to_download = [
        item["path"]
        for item in tree_data.get("tree", [])
        if item["type"] == "blob"
        and any(
            item["path"] == folder or item["path"].startswith(folder + "/")
            for folder in FOLDERS
        )
    ]

    if not files_to_download:
        print("No files found in the specified folders.")
        sys.exit(1)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    total = len(files_to_download)
    print(f"Downloading {total} file(s) into {OUTPUT_DIR}/\n")

    for i, path in enumerate(files_to_download, 1):
        print(f"  [{i}/{total}] {path}")
        download_file(path)

    print(f"\nDone. Files saved to {OUTPUT_DIR.resolve()}/")
    for folder in FOLDERS:
        dest = OUTPUT_DIR / folder
        if dest.exists():
            count = sum(1 for _ in dest.rglob("*") if _.is_file())
            print(f"  {dest}/ — {count} file(s)")


if __name__ == "__main__":
    main()
