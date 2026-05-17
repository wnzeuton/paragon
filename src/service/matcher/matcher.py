import csv
import numpy as np
from pathlib import Path
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer

from src.service.preprocessing.text import normalize, tokenize, extract_attributes

W_SEM  = 0.7
W_LEX  = 0.2
W_ATTR = 0.1

ATTR_IMPORTANCE = {
    'thread':   3,
    'type':     2,
    'material': 2,
    'length':   2,
    'finish':   1,
}

ATTR_PENALTY = 0.15  # deducted when query specifies attr but item has none

_MODEL_NAME = 'all-MiniLM-L6-v2'


def _thread_matches(query_val: str, catalog_val: str) -> bool:
    """Prefix-match thread sizes: query '7/16' matches catalog '7/16-14'."""
    q = query_val.lower().rstrip('-').rstrip('.')
    c = catalog_val.lower()
    return c.startswith(q) or q.startswith(c)


def _finish_matches(query_val: str, catalog_val: str) -> bool:
    """Partial match: query 'zinc' matches 'yellow zinc' or 'mechanical zinc'."""
    return query_val in catalog_val or catalog_val in query_val


def _material_matches(query_val: str, catalog_val: str) -> bool:
    """Partial match: query 'stainless' matches '18-8 stainless steel'."""
    return query_val in catalog_val or catalog_val in query_val


def _attr_matches(attr: str, query_val: str, catalog_val: str) -> bool:
    if attr == 'thread':
        return _thread_matches(query_val, catalog_val)
    if attr == 'finish':
        return _finish_matches(query_val, catalog_val)
    if attr == 'material':
        return _material_matches(query_val, catalog_val)
    return query_val == catalog_val


def _attr_score(query_attrs: dict, catalog_attrs: dict) -> tuple[float, list]:
    """
    Compute attribute score ∈ [0,1] and collect mismatch notes.
    Returns (score, notes).
    """
    total_weight = 0
    matched_weight = 0.0
    notes = []

    for attr, importance in ATTR_IMPORTANCE.items():
        q_val = query_attrs.get(attr)
        if q_val is None:
            continue  # user didn't mention this attr → neutral contribution
        c_val = catalog_attrs.get(attr)
        total_weight += importance
        if c_val is None:
            matched_weight -= ATTR_PENALTY * importance
            notes.append(f'{attr.capitalize()} not specified in this item')
        elif _attr_matches(attr, q_val, c_val):
            matched_weight += importance
        else:
            notes.append(f'{attr.capitalize()} mismatch: query has "{q_val}", item has "{c_val}"')

    if total_weight == 0:
        return 0.5, []  # no attrs specified → neutral

    score = matched_weight / total_weight
    return float(np.clip(score, 0.0, 1.0)), notes


class CatalogMatcher:
    def __init__(self, model_name: str = _MODEL_NAME):
        self._model = SentenceTransformer(model_name)
        self._catalog: list[dict] = []
        self._norm_texts: list[str] = []
        self._embeddings: np.ndarray | None = None
        self._tfidf: TfidfVectorizer | None = None
        self._tfidf_matrix = None

    def load_catalog(self, path: str):
        p = Path(path)
        raw_items = []
        with open(p, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get('active', 'Y').strip().upper() != 'Y':
                    continue
                raw_items.append(row)

        # Deduplicate by normalized description (keep first occurrence)
        seen: set[str] = set()
        catalog = []
        for row in raw_items:
            desc = row.get('catalog_description', '').strip()
            key = normalize(desc)
            if key in seen:
                continue
            seen.add(key)
            catalog.append({
                'id':    row.get('catalog_id', '').strip(),
                'sku':   row.get('sku', '').strip(),
                'title': desc,
                'attrs': extract_attributes(desc),
            })

        self._catalog = catalog
        self._norm_texts = [normalize(item['title']) for item in catalog]
        self._build_index()

    def _build_index(self):
        texts = self._norm_texts
        if not texts:
            return

        self._embeddings = self._model.encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=False,
            batch_size=64,
        )

        self._tfidf = TfidfVectorizer(
            analyzer='char_wb',
            ngram_range=(3, 5),
            min_df=1,
            sublinear_tf=True,
        )
        self._tfidf_matrix = self._tfidf.fit_transform(texts)

    def search(self, query: str, n: int = 3) -> list[dict]:
        if not self._catalog or self._embeddings is None:
            return []

        query_norm = normalize(query)
        query_attrs = extract_attributes(query)
        query_tokens = set(tokenize(query_norm))

        # --- Semantic retrieval (top-20 candidates) ---
        q_vec = self._model.encode([query_norm], normalize_embeddings=True)
        sem_all = (q_vec @ self._embeddings.T).flatten()
        candidate_size = min(50, len(self._catalog))
        top_idx = np.argsort(sem_all)[::-1][:candidate_size]

        # --- Lexical signal (char n-gram TF-IDF) ---
        q_tfidf = self._tfidf.transform([query_norm])
        lex_scores = cosine_similarity(q_tfidf, self._tfidf_matrix[top_idx]).flatten()

        # --- Attribute signal ---
        sem_scores = sem_all[top_idx]

        results = []
        for i, idx in enumerate(top_idx):
            item = self._catalog[idx]
            attr_sc, notes = _attr_score(query_attrs, item['attrs'])

            combined = float(np.clip(
                W_SEM * sem_scores[i] + W_LEX * lex_scores[i] + W_ATTR * attr_sc,
                0.0, 1.0,
            ))

            highlights = [t for t in query_tokens if t in self._norm_texts[idx]]

            results.append({
                'id':         item['id'],
                'sku':        item['sku'],
                'title':      item['title'],
                'score':      round(combined, 4),
                'breakdown':  {
                    'semantic':   round(float(sem_scores[i]), 4),
                    'lexical':    round(float(lex_scores[i]), 4),
                    'attribute':  round(attr_sc, 4),
                },
                'highlights': highlights,
                'notes':      notes,
            })

        results.sort(key=lambda r: r['score'], reverse=True)
        return results[:n]

    @property
    def catalog_size(self) -> int:
        return len(self._catalog)
