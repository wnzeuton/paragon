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

## Design

### Preprocessing

Queries and catalog descriptions go through the same normalization pipeline before any comparison, so both sides are "speaking the same language" when scoring happens.

**(1) Phrase-level substitution**

Multi-token abbreviations are expanded first using regex patterns applied to the full string. This pass runs before tokenization because splitting on whitespace first would lose the context needed to expand multi-word shorthands — `"18-8 ss"` needs to be seen as a unit to correctly become `"eighteen eight stainless steel"`. Patterns are ordered most-specific first so a generic pattern doesn't fire before a more specific one gets the chance.

*Limitation:* The expansion list is manually curated. This works for a known, bounded domain like fasteners, but a rapidly changing catalog with new or unfamiliar abbreviations would require ongoing maintenance. In practice, logging queries that return low-confidence results and periodically scanning for high-frequency unrecognized tokens would surface gaps in the list without requiring guesswork.

**(2) Token-level substitution**

Single-token abbreviations that weren't caught by phrase-level substitution are swapped out via a dictionary lookup after splitting on whitespace. Numeric tokens and thread sizes (e.g. `M8`, `3/8-16`) are explicitly skipped to avoid corrupting specs.

**(3) Attribute extraction**

Structured attributes — thread size, length, fastener type, material, finish — are extracted from the *original, un-normalized* text using regex patterns ordered longest-match-first. Running on raw text rather than normalized text avoids casing issues with metric thread sizes (`M8`) and means the patterns can handle abbreviated forms directly.

If the query doesn't specify an attribute, that attribute contributes nothing to the score in either direction — it doesn't penalize catalog items that do have that attribute. Attributes are only used as a signal when the query explicitly mentions them.

*Known limitation:* If the query specifies an attribute (e.g. material) that has zero coverage anywhere in the catalog, every item takes the same small penalty and the attribute has no discriminating effect. The system doesn't currently detect or surface this gap. A straightforward fix would be to precompute which attributes have any catalog coverage at index build time and flag catalog-wide gaps in the search response, rather than silently applying a uniform penalty.

---

### Retrieval

**(1) Semantic shortlist**

Embedding similarity narrows the full catalog down to the top 20 candidates. This is the coarse retrieval step.

**(2) Rerank**

Lexical and attribute scoring run only over those 20 candidates to produce the final ranking.

At ~1k items the two-stage approach doesn't make a measurable difference in speed, but the pattern scales — if the catalog grew to hundreds of thousands of items, running attribute extraction and TF-IDF over everything on every query would be expensive. Semantic search is cheap to run at scale.

---

### Scoring

Final score = `clip(0.7·sem + 0.2·lex + 0.1·attr, 0, 1)`

**(1) Semantic similarity — 70%**

Each query and catalog item is encoded using `all-MiniLM-L6-v2`. Cosine similarity between the query embedding and each candidate's embedding forms the primary signal. Semantic embeddings are the strongest signal here because they bridge vocabulary gaps that exact or fuzzy string matching can't — a customer typing "SHCS" can match "socket head cap screw" even if the abbreviation isn't in the expansion list.

**(2) Char n-gram TF-IDF — 20%**

Text is broken into overlapping character sequences of length 3–5 instead of whole words. TF-IDF then measures how distinctive those sequences are across the catalog. This catches fuzzy matches that semantics would score equally — abbreviations, misspellings, and partial tokens all share many overlapping character patterns with their full forms. N-grams are extracted within word boundaries (`char_wb`) so character sequences don't bleed across unrelated words.

The embeddings are treated as the primary signal and TF-IDF as a tiebreaker, not a co-equal signal. This is because semantic similarity already handles the bulk of vocabulary variance; TF-IDF adds precision at the margin.

**(3) Attribute matching — 10%**

Extracted attributes from the query are compared against extracted attributes from each catalog candidate. Attributes use fuzzy matching rules appropriate to their type — thread sizes use prefix matching (so `3/8` matches `3/8-16`, treating an underspecified query as compatible with a fully specified catalog item), material and finish use substring matching.

Two distinct penalties apply:
- **Mismatch:** query specifies an attribute and the catalog item has a different value — larger penalty.
- **Absent:** query specifies an attribute and the catalog item doesn't mention it at all — smaller penalty. This avoids rewarding under-specified catalog items that would otherwise score well on many queries simply by not committing to any specs.

*Note on thresholds:* The weights (70/20/10) and penalty values are set by intuition, not tuned against labeled data. With a labeled evaluation set, you'd run the eval suite against a grid of values and select what maximizes top-1 accuracy.

---

## Confidence score

Shown as a percentage on each result card:
- **≥ 70%** — strong match
- **40–69%** — moderate match
- **< 40%** — low confidence; a banner suggests refining the query

Confidence is most meaningful as a relative signal. The gap between the top result and the second result indicates how clearly the query distinguished one item from the rest. A cluster of similar scores across the top results suggests the query was too vague to discriminate well.

---

## Testing

```bash
# Unit tests (no catalog required)
pytest tests/unit/

# Accuracy evaluation (requires catalog)
python tests/eval/eval.py
```

---

## API

```
GET /search?q=<query>&n=3
GET /health
```

Response fields: `id`, `sku`, `title`, `score`, `breakdown` (semantic/lexical/attribute), `highlights`, `notes`.
