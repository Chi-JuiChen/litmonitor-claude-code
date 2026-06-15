#!/usr/bin/env python3
"""
Render papers_scored.json (or papers_raw.json) as markdown sorted by score.

Usage:
    python show_results.py               # all papers
    python show_results.py --min-score 7 # score 7-10 only
    python show_results.py --json        # raw JSON output
"""

import argparse
import json
from pathlib import Path


def truncate(text, n):
    if len(text) <= n:
        return text
    return text[:n - 1] + '…'


def main():
    parser = argparse.ArgumentParser(description='Display scored papers as markdown')
    parser.add_argument('--min-score', type=int, default=1)
    parser.add_argument('--json', action='store_true', dest='as_json')
    parser.add_argument('--input', default='papers_scored.json')
    args = parser.parse_args()

    path = Path(args.input)
    if not path.exists():
        path = Path('papers_raw.json')
    if not path.exists():
        print('No papers_scored.json or papers_raw.json found. Run fetch_papers.py first.')
        return

    data = json.loads(path.read_text(encoding='utf-8'))
    meta = data.get('metadata', {})
    papers = data.get('papers', [])

    visible = [p for p in papers
               if p.get('score') is not None and (p.get('score') or 0) >= args.min_score]
    visible.sort(key=lambda p: (-(p.get('score') or 0), p.get('date', ''), p.get('title', '')))

    if args.as_json:
        print(json.dumps({'metadata': meta, 'papers': visible}, indent=2, ensure_ascii=False))
        return

    fetched_at = (meta.get('fetched_at') or '')[:10]
    totals = meta.get('totals', {})
    total = totals.get('total', len(papers))
    cached = totals.get('cached', 0)
    new = total - cached

    print(f'## Literature Summary — {fetched_at}')
    print(f'{total} papers fetched ({cached} cached · {new} scored this run)', end='')
    print(f' · showing score ≥ {args.min_score}\n' if args.min_score > 1 else '\n')

    tiers = [
        (9, 10, 'High Priority'),
        (7, 8,  'Worth Reading'),
        (5, 6,  'Peripheral'),
        (1, 4,  'Low Relevance'),
    ]

    for lo, hi, label in tiers:
        tier = [p for p in visible if lo <= (p.get('score') or 0) <= hi]
        if not tier:
            continue

        print(f'### Score {lo}–{hi}: {label} ({len(tier)} papers)\n')

        if lo >= 5:
            print('| Score | Title | Authors | Journal | Date |')
            print('|------:|-------|---------|---------|------|')
            for p in tier:
                score = p.get('score', '?')
                title = truncate(p.get('title') or 'Untitled', 70)
                url = p.get('url', '')
                title_cell = f'[{title}]({url})' if url else title
                authors = truncate(p.get('authors') or '', 35)
                journal = truncate(p.get('journal') or '', 30)
                date = p.get('date', '')
                print(f'| {score} | {title_cell} | {authors} | {journal} | {date} |')
            print()

            for p in tier:
                if p.get('reason'):
                    print(f'> **{truncate(p.get("title") or "", 55)}**: {p["reason"]}')
            print()

        else:
            for p in tier:
                score = p.get('score', '?')
                title = truncate(p.get('title') or 'Untitled', 80)
                print(f'- [{score}] {title}')
            print()


if __name__ == '__main__':
    main()
