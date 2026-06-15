#!/usr/bin/env python3
"""
Update score_cache.json from papers_scored.json.
Run this after Claude finishes scoring to persist results for future runs.

Usage:
    python update_cache.py
"""

import json
from datetime import datetime, timezone
from pathlib import Path


def utcnow():
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def main():
    scored_path = Path('papers_scored.json')
    cache_path = Path('score_cache.json')

    if not scored_path.exists():
        print('ERROR: papers_scored.json not found. Ask Claude to score the papers first.')
        return

    scored = json.loads(scored_path.read_text(encoding='utf-8'))

    try:
        cache = json.loads(cache_path.read_text(encoding='utf-8'))
    except FileNotFoundError:
        cache = {}

    cache.setdefault('_meta', {'version': '1.0', 'total_entries': 0})

    added = 0
    for paper in scored.get('papers', []):
        pid = paper.get('paper_id')
        score = paper.get('score')
        if pid and score is not None and pid not in cache:
            cache[pid] = {
                'score': int(score),
                'reason': paper.get('reason') or '',
                'scored_at': paper.get('scored_at') or utcnow(),
            }
            added += 1

    cache['_meta']['last_updated'] = utcnow()
    cache['_meta']['total_entries'] = len(cache) - 1
    cache['_meta']['version'] = '1.0'

    cache_path.write_text(json.dumps(cache, indent=2, ensure_ascii=False), encoding='utf-8')
    print(f'Cache updated: +{added} new entries, {cache["_meta"]["total_entries"]} total')
    print('To re-score a paper: delete its paper_id key from score_cache.json, then re-fetch.')


if __name__ == '__main__':
    main()
