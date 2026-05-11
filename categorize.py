#!/usr/bin/env python3
"""Categorize magpie_hf.json scenarios using the Gemini API."""

import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

CATEGORIES_FILE = Path("categories.json")
DATASET_FILE = Path("scenarios/magpie_hf.json")
API_KEY = os.environ.get("GEMINI_API_KEY", "")
MODEL = "gemini-2.0-flash"
BATCH_SIZE = 10

SYSTEM_PROMPT = """\
You are a scenario categorization assistant. Given negotiation scenarios, assign each a single broad industry or domain category.

Categories must be broad — prefer the industry/sector over the specific activity:
  Good: "Real estate", "Legal", "Medical", "Technology", "Finance", "Military",
        "Environment", "Human resources", "Transportation", "Entertainment",
        "Education", "Research", "Supply chain", "Policy", "Energy"
  Too narrow: "Salary negotiation" (use "Human resources"), "Patent dispute" (use "Legal")

Example categorizations from this dataset:
  filename: timeline_1
  scenario: High-profile product launch timeline negotiation for 'Aura', an AI-powered smart home hub...
  task: Stakeholders must agree on a launch date, feature list, production volume, and marketing budget.
  → category: "Product launch"

  filename: medical_collaboration_1
  scenario: Doctors collaborating on a complex patient case with conflicting treatment opinions...
  task: Reach consensus on a treatment plan.
  → category: "Medical"

  filename: policy_1
  scenario: Government agencies negotiating a new environmental regulation...
  task: Draft a unified policy document.
  → category: "Policy"

Rules:
- Title case for every category (e.g. "Real estate", not "real estate" or "REAL ESTATE")
- One category per scenario — the single best fit
- Return ONLY a valid JSON array of objects with exactly "filename" and "category" keys, in the same order as the input
"""


def call_gemini(batch: list[dict]) -> list[dict]:
    parts = []
    for s in batch:
        parts.append(
            f"filename: {s['file_name']}\n"
            f"scenario: {s['scenario']}\n"
            f"task: {s['task']}"
        )
    user_prompt = "\n\n---\n\n".join(parts)
    user_prompt += (
        "\n\nReturn a JSON array with one {\"filename\": ..., \"category\": ...} "
        "object per scenario, in the same order."
    )

    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{MODEL}:generateContent?key={API_KEY}"
    )
    body = {
        "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": [{"parts": [{"text": user_prompt}]}],
        "generationConfig": {"responseMimeType": "application/json"},
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        result = json.loads(resp.read())

    text = result["candidates"][0]["content"]["parts"][0]["text"]
    return json.loads(text)


def main() -> None:
    if not API_KEY:
        print("Error: GEMINI_API_KEY environment variable is not set.")
        return

    with open(CATEGORIES_FILE) as f:
        cat_data = json.load(f)

    done = {c["filename"] for c in cat_data["categories"]}

    with open(DATASET_FILE) as f:
        dataset = json.load(f)

    all_rows = dataset.get("train", [])
    todo = [r for r in all_rows if r["file_name"] not in done]

    print(f"Total scenarios : {len(all_rows)}")
    print(f"Already done    : {len(done)}")
    print(f"To process      : {len(todo)}")
    print()

    for i in range(0, len(todo), BATCH_SIZE):
        batch = todo[i : i + BATCH_SIZE]
        end = min(i + BATCH_SIZE, len(todo))
        print(f"[{end}/{len(todo)}] processing batch...", end=" ", flush=True)

        retries = 3
        for attempt in range(retries):
            try:
                results = call_gemini(batch)
                cat_data["categories"].extend(results)
                with open(CATEGORIES_FILE, "w") as f:
                    json.dump(cat_data, f, indent=4)
                print(f"ok — {[r['category'] for r in results]}")
                break
            except urllib.error.HTTPError as e:
                body = e.read().decode()
                if e.code == 429 and attempt < retries - 1:
                    wait = 10 * (attempt + 1)
                    print(f"rate limited, retrying in {wait}s...", end=" ", flush=True)
                    time.sleep(wait)
                else:
                    print(f"HTTP {e.code}: {body}")
                    return
            except Exception as e:
                print(f"error: {e}")
                return

        if end < len(todo):
            time.sleep(0.5)

    print(f"\nDone. Total categories in file: {len(cat_data['categories'])}")


if __name__ == "__main__":
    main()
