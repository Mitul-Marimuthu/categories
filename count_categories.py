#!/usr/bin/env python3
import json
from collections import Counter
from pathlib import Path

with open("results/categories.json") as f:
    data = json.load(f)

counts = Counter(c["category"] for c in data["categories"])
result = [{"category": cat, "count": n} for cat, n in counts.most_common()]

Path("results/category_counts.json").write_text(json.dumps(result, indent=4))
print(f"Saved {len(result)} categories ({sum(counts.values())} total scenarios)")
for r in result:
    print(f"  {r['count']:>3}  {r['category']}")

# dummy commnet