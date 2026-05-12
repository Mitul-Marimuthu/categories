#!/usr/bin/env python3
"""
Pipeline: for each domain category, generate 5 privacy definitions via Gemini,
then aggregate them into a single synthesized definition.
Output: privacy_definitions.json
"""

import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path


def _load_env(path: Path = Path(".env")) -> None:
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))


_load_env()

API_KEY = os.environ.get("GEMINI_API_KEY", "")
MODEL = "gemini-2.5-flash"
ATTEMPTS = 5
DELAY = 2  # seconds between calls to avoid rate limiting
OUTPUT_FILE = Path("privacy_definitions.json")
CATEGORIES_FILE = Path("category_counts.json")

GENERATION_SYSTEM_PROMPT = """\
You are a privacy and data sensitivity expert. Your job is to analyze a specific \
industry or domain and identify what kinds of information arise in negotiation \
scenarios within that domain — and which of those are sensitive vs. non-sensitive.

Think carefully about:
- What data is exchanged or discussed between parties during negotiations
- What a party would want to keep confidential vs. what is routine to share
- What regulations or norms govern data sensitivity in this domain

Return ONLY valid JSON in this exact shape:
{
  "sensitive_data": [
    "list of specific data types considered private or sensitive in this domain"
  ],
  "non_sensitive_data": [
    "list of specific data types that are routine, public, or non-sensitive"
  ],
  "key_concerns": [
    "list of the main privacy risks or concerns unique to this domain"
  ],
  "summary": "2-3 sentence definition of what privacy means in this domain context"
}
"""

AGGREGATION_SYSTEM_PROMPT = """\
You are synthesizing five independently generated privacy analyses for the same \
domain into a single definitive definition. Treat this like taking the mean: \
surface the themes that appear consistently across all five, reconcile minor \
disagreements by finding the common ground, and include anything that appeared \
in at least three of the five analyses.

Do not just concatenate. Deduplicate, generalize, and synthesize.

Return ONLY valid JSON in this exact shape:
{
  "sensitive_data": [
    "deduplicated, synthesized list of sensitive data types"
  ],
  "non_sensitive_data": [
    "deduplicated, synthesized list of non-sensitive data types"
  ],
  "key_concerns": [
    "deduplicated, synthesized list of key privacy concerns"
  ],
  "summary": "3-4 sentence synthesized definition capturing the consensus across all five analyses"
}
"""


def call_gemini(system_prompt: str, user_prompt: str, retries: int = 4) -> dict:
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{MODEL}:generateContent?key={API_KEY}"
    )
    body = {
        "system_instruction": {"parts": [{"text": system_prompt}]},
        "contents": [{"parts": [{"text": user_prompt}]}],
        "generationConfig": {"responseMimeType": "application/json"},
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                result = json.loads(resp.read())
            text = result["candidates"][0]["content"]["parts"][0]["text"]
            return json.loads(text)
        except urllib.error.HTTPError as e:
            body_text = e.read().decode()
            if e.code == 429 and attempt < retries - 1:
                # Parse retry delay from error if available, else exponential backoff
                wait = 15 * (2 ** attempt)
                print(f"\n    rate limited — waiting {wait}s...", end=" ", flush=True)
                time.sleep(wait)
            else:
                raise RuntimeError(f"HTTP {e.code}: {body_text}") from e

    raise RuntimeError("Exhausted retries")


def generate_definition(category: str) -> dict:
    prompt = (
        f"Domain: {category}\n\n"
        f"Analyze privacy and data sensitivity for negotiation scenarios in the "
        f"'{category}' domain."
    )
    return call_gemini(GENERATION_SYSTEM_PROMPT, prompt)


def aggregate_definitions(category: str, raw: list[dict]) -> dict:
    numbered = "\n\n".join(
        f"Analysis {i + 1}:\n{json.dumps(r, indent=2)}" for i, r in enumerate(raw)
    )
    prompt = (
        f"Domain: {category}\n\n"
        f"Here are five independently generated privacy analyses for this domain. "
        f"Synthesize them into a single definitive definition.\n\n{numbered}"
    )
    return call_gemini(AGGREGATION_SYSTEM_PROMPT, prompt)


def load_output() -> dict:
    if OUTPUT_FILE.exists():
        with open(OUTPUT_FILE) as f:
            return json.load(f)
    return {}


def save_output(data: dict) -> None:
    with open(OUTPUT_FILE, "w") as f:
        json.dump(data, f, indent=4)


def main() -> None:
    if not API_KEY:
        print("Error: GEMINI_API_KEY is not set.")
        return

    with open(CATEGORIES_FILE) as f:
        categories = [row["category"] for row in json.load(f)]

    output = load_output()

    for cat_idx, category in enumerate(categories):
        print(f"\n[{cat_idx + 1}/{len(categories)}] {category}")

        entry = output.get(category, {})

        # --- Generation phase ---
        raw = entry.get("raw", [])
        for attempt in range(len(raw), ATTEMPTS):
            print(f"  generating {attempt + 1}/{ATTEMPTS}...", end=" ", flush=True)
            try:
                definition = generate_definition(category)
                raw.append(definition)
                entry["raw"] = raw
                output[category] = entry
                save_output(output)
                print("ok")
            except RuntimeError as e:
                print(f"error: {e}")
                return
            if attempt < ATTEMPTS - 1:
                time.sleep(DELAY)

        # --- Aggregation phase ---
        if "aggregated" not in entry:
            print(f"  aggregating...", end=" ", flush=True)
            try:
                time.sleep(DELAY)
                entry["aggregated"] = aggregate_definitions(category, raw)
                output[category] = entry
                save_output(output)
                print("ok")
            except RuntimeError as e:
                print(f"error: {e}")
                return
        else:
            print("  already aggregated — skipped")

        if cat_idx < len(categories) - 1:
            time.sleep(DELAY)

    print(f"\nDone. Results saved to {OUTPUT_FILE}")
    print(f"Categories completed: {sum(1 for v in output.values() if 'aggregated' in v)}/{len(categories)}")


if __name__ == "__main__":
    main()
