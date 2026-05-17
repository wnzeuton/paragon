"""
Evaluation script: MRR, P@1, P@3 against labeled test cases.
Usage: python tests/eval/eval.py [--catalog data/catalog.csv] [--cases tests/eval/test_cases.json]
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.service.matcher.matcher import CatalogMatcher


def reciprocal_rank(result_ids: list[str], expected_ids: list[str]) -> float:
    for i, rid in enumerate(result_ids, start=1):
        if rid in expected_ids:
            return 1.0 / i
    return 0.0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--catalog', default='data/catalog.csv')
    parser.add_argument('--cases',   default='tests/eval/test_cases.json')
    parser.add_argument('--n',       type=int, default=3)
    args = parser.parse_args()

    print(f'Loading catalog from {args.catalog} …')
    matcher = CatalogMatcher()
    matcher.load_catalog(args.catalog)
    print(f'{matcher.catalog_size} active items indexed.\n')

    with open(args.cases) as f:
        test_cases = json.load(f)

    rrs, p1s, p3s = [], [], []
    correct_scores = []

    for tc in test_cases:
        query = tc['query']
        expected = set(tc['expected_ids'])
        results = matcher.search(query, n=args.n)
        result_ids = [r['id'] for r in results]
        scores     = [r['score'] for r in results]

        rr = reciprocal_rank(result_ids, expected)
        hit1 = any(rid in expected for rid in result_ids[:1])
        hit3 = any(rid in expected for rid in result_ids[:3])

        rrs.append(rr)
        p1s.append(float(hit1))
        p3s.append(float(hit3))

        # Score of the first correct hit (for calibration)
        for rid, sc in zip(result_ids, scores):
            if rid in expected:
                correct_scores.append(sc)
                break

        status = '✓' if rr > 0 else '✗'
        rank_str = f'rank {int(1/rr)}' if rr > 0 else 'not found'
        print(f'  {status} "{query}"')
        print(f'    → {rank_str} | top-3: {result_ids}')
        print(f'    → scores: {[r["score"] for r in results]}')

    print()
    print(f'MRR   : {sum(rrs)/len(rrs):.3f}')
    print(f'P@1   : {sum(p1s)/len(p1s):.3f}')
    print(f'P@3   : {sum(p3s)/len(p3s):.3f}')
    if correct_scores:
        print(f'Correct-item scores: min={min(correct_scores):.3f}  mean={sum(correct_scores)/len(correct_scores):.3f}  max={max(correct_scores):.3f}')
        print(f'  → Low-confidence threshold (0.40) covers items scoring ≥ 0.40')


if __name__ == '__main__':
    main()
