#!/usr/bin/env python3
"""
LitMonitor Claude — paper fetcher

Fetches papers from OpenAlex (journals) and arXiv, enriches missing abstracts
via Semantic Scholar, checks the score cache, and writes papers_raw.json for
Claude Code to score in-session (no extra API cost).

Usage:
    python fetch_papers.py               # use profile.yaml
    python fetch_papers.py --days 30     # override days_back
    python fetch_papers.py --force       # ignore score cache
    python fetch_papers.py --no-enrich   # skip Semantic Scholar
"""

import argparse
import json
import re
import sys
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

# ── YAML loading ──────────────────────────────────────────────────────────────

def _parse_yaml_simple(text):
    """Fallback YAML parser for the exact profile.yaml schema.
    Handles: key: value, folded scalars (key: >), block lists (key:\n  - item).
    Does NOT handle anchors, flow style, or deep nesting.
    """
    lines = text.splitlines()
    result = {}
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            i += 1
            continue

        m = re.match(r'^([a-zA-Z_][a-zA-Z0-9_]*):\s*(.*)', line)
        if not m:
            i += 1
            continue

        key, value_part = m.group(1), m.group(2).strip()

        if value_part == '>':
            i += 1
            acc = []
            while i < len(lines):
                nl = lines[i]
                if nl and not nl[0].isspace():
                    break
                content = nl.strip()
                if content and not content.startswith('#'):
                    acc.append(content)
                i += 1
            result[key] = '\n'.join(acc)

        elif not value_part:
            # Block list or empty value
            i += 1
            items = []
            while i < len(lines):
                nl = lines[i]
                if not nl.strip() or nl.strip().startswith('#'):
                    i += 1
                    continue
                m_item = re.match(r'^\s+-\s+(.*)', nl)
                if m_item:
                    items.append(m_item.group(1).strip())
                    i += 1
                elif nl[0].isspace():
                    i += 1
                else:
                    break
            result[key] = items

        else:
            # Simple scalar; strip inline comment
            val = value_part.split(' #')[0].strip().strip('"').strip("'")
            if re.match(r'^\d+$', val):
                result[key] = int(val)
            elif val.lower() in ('true', 'yes'):
                result[key] = True
            elif val.lower() in ('false', 'no'):
                result[key] = False
            else:
                result[key] = val
            i += 1

    return result


def load_profile(path):
    text = Path(path).read_text(encoding='utf-8')
    try:
        import yaml
        data = yaml.safe_load(text)
    except ImportError:
        data = _parse_yaml_simple(text)

    for field in ('prioritize', 'transferable_methods', 'downgrade',
                  'priority_authors', 'research_context'):
        if data.get(field) is None:
            data[field] = ''

    journals_raw = data.get('journals', [])
    journals_parsed = []
    for line in (journals_raw if isinstance(journals_raw, list) else []):
        if isinstance(line, str) and '|' in line:
            name, ident = line.split('|', 1)
            journals_parsed.append((name.strip(), ident.strip()))
    data['journals_parsed'] = journals_parsed

    return data


# ── Cache ─────────────────────────────────────────────────────────────────────

def load_cache(path='score_cache.json'):
    try:
        return json.loads(Path(path).read_text(encoding='utf-8'))
    except FileNotFoundError:
        return {}


# ── Paper ID normalization ────────────────────────────────────────────────────

_DOI_RE = re.compile(r'doi\.org/(.+?)(?:\s|$)', re.I)
_ARXIV_RE = re.compile(r'arxiv\.org/abs/([^\s?#]+)', re.I)
_ARXIV_VER = re.compile(r'v\d+$')


def make_paper_id(url='', oa_id='', arxiv_id=''):
    if url:
        m = _DOI_RE.search(url)
        if m:
            return 'doi:' + m.group(1).lower().rstrip('/')
        m = _ARXIV_RE.search(url)
        if m:
            return 'arxiv:' + _ARXIV_VER.sub('', m.group(1))
    if arxiv_id:
        return 'arxiv:' + _ARXIV_VER.sub('', arxiv_id)
    if oa_id:
        return 'oa:' + oa_id.split('/')[-1]
    return None


# ── Abstract reconstruction ───────────────────────────────────────────────────

def reconstruct_abstract(inverted):
    if not inverted:
        return ''
    pos_word = {}
    for word, positions in inverted.items():
        for pos in positions:
            pos_word[int(pos)] = word
    text = ' '.join(pos_word[k] for k in sorted(pos_word))
    return text.removeprefix('Abstract ').strip()


# ── HTTP helper ───────────────────────────────────────────────────────────────

def _get_json(url, timeout=20, email=''):
    headers = {'User-Agent': f'LitMonitorClaude/1.0 (mailto:{email})'}
    req = Request(url, headers=headers)
    with urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())


def _post_json(url, body, timeout=20):
    req = Request(url, data=json.dumps(body).encode(),
                  headers={'Content-Type': 'application/json'}, method='POST')
    with urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())


# ── OpenAlex ──────────────────────────────────────────────────────────────────

def fetch_openalex(identifier, journal_name, cutoff_date, email):
    if re.match(r'S\d+$', identifier):
        filter_str = f'primary_location.source.id:https://openalex.org/{identifier}'
    elif re.match(r'ISSN:', identifier, re.I):
        issn = identifier.split(':', 1)[1].strip()
        filter_str = f'primary_location.source.issn:{issn}'
    else:
        filter_str = f'primary_location.source.issn:{identifier}'

    cutoff_str = cutoff_date.strftime('%Y-%m-%d')
    fields = 'id,title,authorships,abstract_inverted_index,primary_location,publication_date,doi'
    base = (f'https://api.openalex.org/works'
            f'?filter={filter_str},from_publication_date:{cutoff_str}'
            f'&select={fields}&per-page=200&mailto={email}')

    results = []
    cursor = '*'
    while cursor:
        try:
            data = _get_json(base + f'&cursor={cursor}', email=email)
        except Exception as e:
            print(f'  WARNING: OpenAlex error for {journal_name}: {e}', file=sys.stderr)
            break

        for work in data.get('results', []):
            doi_url = work.get('doi') or ''
            oa_id = work.get('id', '')
            paper_id = make_paper_id(doi_url, oa_id)
            if not paper_id:
                continue

            authors = ', '.join(
                a.get('author', {}).get('display_name', '')
                for a in work.get('authorships', [])[:5]
                if a.get('author', {}).get('display_name')
            )

            results.append({
                'paper_id': paper_id,
                'title': (work.get('title') or '').strip(),
                'authors': authors,
                'abstract': reconstruct_abstract(work.get('abstract_inverted_index')),
                'journal': journal_name,
                'date': work.get('publication_date', ''),
                'url': doi_url or f'https://openalex.org/{oa_id.split("/")[-1]}',
                'source': 'openalex',
            })

        cursor = data.get('meta', {}).get('next_cursor')
        if not data.get('results'):
            break

    return results


# ── arXiv ─────────────────────────────────────────────────────────────────────

_ATOM = 'http://www.w3.org/2005/Atom'
_ARXNS = 'http://arxiv.org/schemas/atom'


def fetch_arxiv(category, cutoff_date, max_results=300):
    results = []
    start = 0
    batch = 100
    cutoff_ts = cutoff_date.timestamp()

    while start < max_results:
        url = (f'http://export.arxiv.org/api/query'
               f'?search_query=cat:{category}'
               f'&sortBy=submittedDate&sortOrder=descending'
               f'&start={start}&max_results={min(batch, max_results - start)}')
        try:
            raw = Request(url)
            with urlopen(raw, timeout=30) as resp:
                content = resp.read()
        except Exception as e:
            print(f'  WARNING: arXiv error for {category}: {e}', file=sys.stderr)
            break

        root = ET.fromstring(content)
        entries = root.findall(f'{{{_ATOM}}}entry')
        if not entries:
            break

        too_old = 0
        for entry in entries:
            announce = entry.findtext(f'{{{_ARXNS}}}announce_type', '')
            if announce in ('replace', 'replace-cross'):
                continue

            pub_str = entry.findtext(f'{{{_ATOM}}}published', '')
            try:
                pub_ts = datetime.fromisoformat(pub_str.replace('Z', '+00:00')).timestamp()
            except Exception:
                continue

            if pub_ts < cutoff_ts:
                too_old += 1
                continue

            arxiv_id_raw = entry.findtext(f'{{{_ATOM}}}id', '').split('/abs/')[-1]
            arxiv_id = _ARXIV_VER.sub('', arxiv_id_raw)

            results.append({
                'paper_id': f'arxiv:{arxiv_id}',
                'title': (entry.findtext(f'{{{_ATOM}}}title') or '').replace('\n', ' ').strip(),
                'authors': ', '.join(
                    (a.findtext(f'{{{_ATOM}}}name') or '')
                    for a in entry.findall(f'{{{_ATOM}}}author')
                ),
                'abstract': (entry.findtext(f'{{{_ATOM}}}summary') or '').replace('\n', ' ').strip(),
                'journal': f'arXiv:{category}',
                'date': pub_str[:10],
                'url': f'https://arxiv.org/abs/{arxiv_id}',
                'source': 'arxiv',
            })

        start += batch
        if too_old > len(entries) // 2:
            break
        if start < max_results:
            time.sleep(3)

    return results


# ── Semantic Scholar enrichment ───────────────────────────────────────────────

def enrich_abstracts(papers):
    to_enrich = [(i, p) for i, p in enumerate(papers) if not p.get('abstract', '').strip()]
    if not to_enrich:
        return 0

    id_map = []
    for idx, p in to_enrich:
        m = _DOI_RE.search(p.get('url', ''))
        if m:
            id_map.append((idx, f'DOI:{m.group(1).rstrip("/")}'))
        elif p['paper_id'].startswith('arxiv:'):
            id_map.append((idx, f'ARXIV:{p["paper_id"][6:]}'))

    recovered = 0
    chunk_size = 100
    for ci in range(0, len(id_map), chunk_size):
        chunk = id_map[ci:ci + chunk_size]
        indices, ss_ids = zip(*chunk)
        try:
            results = _post_json(
                'https://api.semanticscholar.org/graph/v1/paper/batch?fields=abstract',
                {'ids': list(ss_ids)},
            )
            for paper_idx, result in zip(indices, results):
                if result and result.get('abstract', '').strip():
                    papers[paper_idx]['abstract'] = result['abstract'].strip()
                    recovered += 1
        except Exception as e:
            print(f'  WARNING: Semantic Scholar error (chunk {ci // chunk_size + 1}): {e}',
                  file=sys.stderr)
        if ci + chunk_size < len(id_map):
            time.sleep(1)

    return recovered


# ── Deduplicate ───────────────────────────────────────────────────────────────

def deduplicate(papers):
    seen = {}
    for p in papers:
        if p['paper_id'] not in seen:
            seen[p['paper_id']] = p
    return list(seen.values())


# ── Main ──────────────────────────────────────────────────────────────────────

def utcnow():
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def main():
    parser = argparse.ArgumentParser(description='Fetch papers for LitMonitor Claude')
    parser.add_argument('--days', type=int, help='Override days_back from profile')
    parser.add_argument('--force', action='store_true', help='Ignore score cache (re-score all)')
    parser.add_argument('--no-enrich', action='store_true', help='Skip Semantic Scholar enrichment')
    parser.add_argument('--profile', default='profile.yaml')
    args = parser.parse_args()

    profile_path = Path(args.profile)
    if not profile_path.exists():
        print('ERROR: profile.yaml not found.', file=sys.stderr)
        print('Open this project in Claude Code — it will run the setup wizard.', file=sys.stderr)
        sys.exit(1)

    profile = load_profile(profile_path)
    cache = load_cache()

    days_back = args.days or profile.get('days_back', 14)
    cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)
    email = profile.get('email', 'anonymous@example.com')
    fetch_ts = utcnow()

    print(f'\n=== LitMonitor Fetch — {fetch_ts} ===')
    print(f'Profile: {profile_path}  (days_back={days_back}, email={email})\n')

    all_papers = []

    journals = profile.get('journals_parsed', [])
    if journals:
        print(f'Fetching from OpenAlex ({len(journals)} journals)...')
        for name, identifier in journals:
            papers = fetch_openalex(identifier, name, cutoff, email)
            print(f'  {name:<42}: {len(papers)} papers')
            all_papers.extend(papers)

    cats = profile.get('arxiv_categories', [])
    if cats:
        print(f'\nFetching from arXiv ({len(cats)} categories)...')
        for cat in cats:
            papers = fetch_arxiv(cat, cutoff)
            print(f'  {cat:<30}: {len(papers)} papers')
            all_papers.extend(papers)
            if len(cats) > 1:
                time.sleep(3)

    before_dedup = len(all_papers)
    all_papers = deduplicate(all_papers)
    print(f'\nDeduplicated: {before_dedup} → {len(all_papers)} unique papers')

    missing_before = sum(1 for p in all_papers if not p.get('abstract', '').strip())
    if not args.no_enrich and missing_before:
        print(f'\nEnriching {missing_before} missing abstracts via Semantic Scholar...')
        recovered = enrich_abstracts(all_papers)
        print(f'  Recovered {recovered}/{missing_before}')

    cached_count = 0
    for p in all_papers:
        entry = cache.get(p['paper_id'])
        p['fetched_at'] = fetch_ts
        if entry and not args.force:
            p.update(cached=True, score=entry['score'],
                     reason=entry['reason'], scored_at=entry['scored_at'])
            cached_count += 1
        else:
            p.update(cached=False, score=None, reason=None, scored_at=None)

    to_score = len(all_papers) - cached_count
    print(f'\nScore cache: {cached_count} already scored, {to_score} need scoring')

    output = {
        'metadata': {
            'fetched_at': fetch_ts,
            'days_back': days_back,
            'cutoff_date': cutoff.strftime('%Y-%m-%d'),
            'profile_path': str(profile_path),
            'totals': {
                'total': len(all_papers),
                'cached': cached_count,
                'to_score': to_score,
            },
        },
        'papers': all_papers,
    }

    Path('papers_raw.json').write_text(
        json.dumps(output, indent=2, ensure_ascii=False), encoding='utf-8'
    )
    print(f'\npapers_raw.json written ({len(all_papers)} papers)')

    if to_score == 0:
        print('\nAll papers already cached. Run: python show_results.py')
    else:
        print(f'\n=== Ready for scoring ===')
        print('Tell Claude Code: "score the papers" or "fetch and score papers"')


if __name__ == '__main__':
    main()
