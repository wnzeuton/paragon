import json
import csv
import io
import pytest
from src.service.matcher.matcher import CatalogMatcher


MINI_CATALOG = [
    {
        'catalog_id': 'CAT-A',
        'sku': 'SKU-A',
        'catalog_description': 'M8-1.25 X 30MM SOCKET HEAD CAP SCREW STEEL ZINC',
        'active': 'Y',
    },
    {
        'catalog_id': 'CAT-B',
        'sku': 'SKU-B',
        'catalog_description': '1/4-20 HEX NUT STEEL PLAIN',
        'active': 'Y',
    },
    {
        'catalog_id': 'CAT-C',
        'sku': 'SKU-C',
        'catalog_description': '3/8-16 FLAT WASHER BRASS HDG',
        'active': 'N',  # inactive
    },
]


def write_mini_catalog(tmp_path, rows=None):
    rows = rows or MINI_CATALOG
    path = tmp_path / 'catalog.csv'
    with open(path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['catalog_id', 'sku', 'catalog_description', 'active'])
        writer.writeheader()
        writer.writerows(rows)
    return str(path)


def test_empty_catalog_returns_empty():
    m = CatalogMatcher()
    assert m.search('M8 socket screw', n=3) == []


def test_inactive_items_excluded(tmp_path):
    path = write_mini_catalog(tmp_path)
    m = CatalogMatcher()
    m.load_catalog(path)
    ids = [r['id'] for r in m.search('flat washer brass', n=3)]
    assert 'CAT-C' not in ids


def test_scores_in_range(tmp_path):
    path = write_mini_catalog(tmp_path)
    m = CatalogMatcher()
    m.load_catalog(path)
    for result in m.search('M8 socket head cap screw zinc', n=3):
        assert 0.0 <= result['score'] <= 1.0


def test_breakdown_keys_present(tmp_path):
    path = write_mini_catalog(tmp_path)
    m = CatalogMatcher()
    m.load_catalog(path)
    results = m.search('hex nut', n=3)
    assert len(results) > 0
    for r in results:
        assert 'semantic' in r['breakdown']
        assert 'lexical'  in r['breakdown']
        assert 'attribute' in r['breakdown']


def test_exact_match_ranks_first(tmp_path):
    path = write_mini_catalog(tmp_path)
    m = CatalogMatcher()
    m.load_catalog(path)
    results = m.search('M8 socket head cap screw steel zinc', n=3)
    assert results[0]['id'] == 'CAT-A'


def test_catalog_size(tmp_path):
    path = write_mini_catalog(tmp_path)
    m = CatalogMatcher()
    m.load_catalog(path)
    # CAT-C is inactive, so only 2 items indexed
    assert m.catalog_size == 2
