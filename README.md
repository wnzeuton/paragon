# Catalog Match

Maps a free-form product description to the top-3 items in a fastener catalog.

## Quick Start

```bash
# 1. Create and activate virtualenv
python -m venv .venv && source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Place your catalog CSV at data/catalog.csv

# 4. Start the backend (from repo root)
CATALOG_PATH=data/catalog.csv uvicorn src.service.api.app:app --reload

# 5. In a separate terminal, start the frontend
cd src/ui/app
npm install
npm run dev
# → Open http://localhost:5173
```

## How it works

Every query goes through three signals, combined as a weighted sum:

| Signal | Weight | Purpose |
|---|---|---|
| Semantic (SentenceTransformers) | 70% | Bridges vocabulary gaps — "SHCS" → "socket head cap screw" |
| Lexical (char n-gram TF-IDF) | 20% | Rewards shared character sequences for partial matches |
| Attribute (regex-extracted fields) | 10% | Boosts items where thread size, material, and finish match |

Final score = `clip(0.7·sem + 0.2·lex + 0.1·attr, 0, 1)`

## Abbreviation handling

Customer queries and catalog descriptions are both normalized through the same expansion map before any comparison. This handles both customer acronyms (SHCS, HHB) and catalog shorthand (HX, SOC, HDG, MZ, YZ).

## Confidence score

Shown as a percentage on each result card:
- **≥ 70%** — strong match
- **40–69%** — moderate match  
- **< 40%** — low confidence; a banner suggests refining the query

## Testing

```bash
# Unit tests (no catalog required)
pytest tests/unit/

# Accuracy evaluation (requires catalog)
python tests/eval/eval.py
```

## API

```
GET /search?q=<query>&n=3
GET /health
```

Response fields: `id`, `sku`, `title`, `score`, `breakdown` (semantic/lexical/attribute), `highlights`, `notes`.
