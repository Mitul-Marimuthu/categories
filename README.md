# Magpie Negotiation Scenarios — Privacy Analysis

This project downloads, categorizes, and generates privacy definitions for negotiation scenarios from the Magpie dataset.

---

## Project Structure

```
.
├── categorize.py                  # Categorizes scenarios by domain using Gemini API
├── categories.json                # Output: per-scenario domain labels (gitignored)
├── count_categories.py            # Counts category frequencies
├── category_counts.json           # Output: category → count mapping
├── generate_privacy_definitions.py # Generates & aggregates privacy definitions per domain
├── privacy_definitions.json       # Output: raw + aggregated definitions (gitignored)
├── scenarios/
│   └── magpie_hf.json             # HuggingFace dataset, 200 scenarios (gitignored)
├── .env                           # API keys (gitignored)
└── README.md
```

---

## Data Sources

### GitHub — gurusha01/magpie
Two folders downloaded from the source repo:
- `data2/` — flat collection of scenario JSON files
- `data/data/` — same scenarios organized by category subdirectory

These were merged into a single flat `scenarios/` folder (gitignored), with `data2/` taking precedence on name conflicts and unique files from `data/data/` added in.

### HuggingFace — jaypasnagasai/magpie
200 negotiation scenarios downloaded via the HuggingFace Datasets Server API (no extra dependencies). Each row contains:

| Field | Description |
|---|---|
| `file_name` | Unique scenario identifier |
| `scenario` | Narrative description of the negotiation context |
| `task` | What the agents must collectively achieve |
| `agent_number` | Number of negotiating parties |
| `agents` | Per-agent roles, descriptions, and private preferences |
| `success_criteria` | Conditions for a successful outcome |

---

## Pipeline

### 1. Categorization (`categorize.py`)

Calls Gemini (`gemini-2.5-flash`) in batches of 10 to assign each scenario a broad domain label.

**Output shape — `categories.json`:**
```json
{
  "categories": [
    { "filename": "timeline_1", "category": "Technology" }
  ]
}
```

**Post-processing applied:**
- Normalized inconsistent casing (e.g. `"Real Estate"` → `"Real estate"`)
- Merged 7 overlapping categories into broader ones:

| Absorbed | Into |
|---|---|
| Art, Sports | Entertainment |
| Travel | Transportation |
| Telecommunications, Product launch | Technology |
| Infrastructure | Urban planning |
| Emergency management | Military |

Final result: **16 categories** across 200 scenarios.

---

### 2. Category Frequency Count (`count_categories.py`)

Reads `categories.json` and produces a sorted frequency table.

**Output — `category_counts.json`:**
```json
[
  { "category": "Technology", "count": 23 },
  { "category": "Policy",     "count": 23 }
]
```

**Final 16 categories:**

| Category | Count |
|---|---:|
| Technology | 23 |
| Policy | 23 |
| Medical | 21 |
| Human resources | 20 |
| Entertainment | 17 |
| Finance | 17 |
| Legal | 13 |
| Transportation | 13 |
| Research | 11 |
| Environment | 10 |
| Real estate | 8 |
| Education | 8 |
| Energy | 5 |
| Supply chain | 5 |
| Military | 4 |
| Urban planning | 2 |

---

### 3. Privacy Definition Generation (`generate_privacy_definitions.py`)

For each of the 16 domain categories, generates **3 independent privacy definitions** then aggregates them into a single synthesized definition.

**Why 3 independent generations?**
LLM outputs are probabilistic. Generating multiple definitions and aggregating them reduces the effect of any single response being incomplete or biased — similar to taking an average.

**Generation prompt asks for:**
- `sensitive_data` — data types considered private in this domain
- `non_sensitive_data` — data types that are routine or public
- `key_concerns` — main privacy risks unique to this domain
- `summary` — 2-3 sentence definition

**Aggregation prompt** synthesizes the 3 definitions by surfacing themes present in at least 2 of 3 responses, deduplicating, and writing a 3-4 sentence consensus summary.

**Output shape — `privacy_definitions.json`:**
```json
{
  "Medical": {
    "raw": [
      { "sensitive_data": [...], "non_sensitive_data": [...], "key_concerns": [...], "summary": "..." },
      { "..." },
      { "..." }
    ],
    "aggregated": {
      "sensitive_data": [...],
      "non_sensitive_data": [...],
      "key_concerns": [...],
      "summary": "..."
    }
  }
}
```

**API notes:**
- Primary: Groq (`llama-3.3-70b-versatile`) — active
- Fallback: Gemini (`gemini-2.5-flash`) — commented out in script, ready to swap back
- Script is **resumable**: saves after every API call; re-running skips completed categories

---

## Setup

1. Clone the repo
2. Add API keys to `.env`:
```
GROQ_API_KEY=your_key_here
GEMINI_API_KEY=your_key_here
```
3. Run the pipeline in order:
```bash
python3 download_hf_dataset.py     # fetch the dataset
python3 categorize.py              # label each scenario
python3 count_categories.py        # compute frequency table
python3 generate_privacy_definitions.py  # generate privacy definitions
```

---

## Gitignored Files

| Path | Reason |
|---|---|
| `scenarios/` | Large dataset files |
| `magpie_data/` | Raw downloaded source data |
| `categories.json` | Generated output |
| `privacy_definitions.json` | Generated output |
| `.env` | API keys |
| `download_hf_dataset.py` | Utility script, not part of core pipeline |
| `download_magpie_data.py` | Utility script, not part of core pipeline |
