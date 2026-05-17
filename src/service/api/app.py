import os
from contextlib import asynccontextmanager
from typing import List

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.service.matcher.matcher import CatalogMatcher

_matcher = CatalogMatcher()
_CATALOG_PATH = os.environ.get('CATALOG_PATH', 'data/catalog.csv')


@asynccontextmanager
async def _lifespan(app: FastAPI):
    if os.path.exists(_CATALOG_PATH):
        print(f'Loading catalog from {_CATALOG_PATH} …')
        _matcher.load_catalog(_CATALOG_PATH)
        print(f'Catalog ready — {_matcher.catalog_size} active items indexed.')
    else:
        print(f'WARNING: catalog not found at {_CATALOG_PATH}. Searches will return empty results.')
    yield


app = FastAPI(title='Catalog Match API', lifespan=_lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_methods=['GET'],
    allow_headers=['*'],
)


class Breakdown(BaseModel):
    semantic:  float
    lexical:   float
    attribute: float


class SearchResult(BaseModel):
    id:         str
    sku:        str
    title:      str
    score:      float
    breakdown:  Breakdown
    highlights: List[str]
    notes:      List[str]


@app.get('/search', response_model=List[SearchResult])
async def search(
    q: str = Query(..., description='Free-form product description'),
    n: int = Query(3, ge=1, le=10, description='Number of results'),
):
    if not q or not q.strip():
        raise HTTPException(status_code=400, detail='Query parameter `q` must not be empty.')
    results = _matcher.search(q.strip(), n=n)
    return results


@app.get('/health')
async def health():
    return {'status': 'ok', 'catalog_size': _matcher.catalog_size}
