# Contributing

Contributions are welcome! Here are the most useful ways to contribute:

## Add a journal or arXiv category

The easiest contribution: if you find a journal or arXiv category that belongs in one of the profile templates, open a PR that adds it.

To find an OpenAlex source ID:
```
https://api.openalex.org/sources?search=<journal+name>
```
Look for the `id` field, e.g. `"id": "https://openalex.org/S137773608"` → use `S137773608`.

## Add a profile template

1. Create `profiles/<field>.yaml` based on an existing template
2. Update `profiles/README.md` with a table entry
3. Submit a PR with a brief description of the field it covers

## Add a new data source

Add a function `fetch_<source>(...)` in `fetch_papers.py` that returns a list of paper dicts.

Required fields per paper:
```python
{
    "paper_id": str,   # unique stable ID: "doi:10.xxx", "arxiv:2606.xxx", or "source:id"
    "title":    str,
    "authors":  str,   # comma-separated display names
    "abstract": str,   # empty string if unavailable
    "journal":  str,   # source name for display
    "date":     str,   # YYYY-MM-DD
    "url":      str,
    "source":   str,   # short identifier, e.g. "crossref", "biorxiv"
}
```

Then call it from `main()` and accumulate results into `all_papers`.

## Bug reports

Open a GitHub issue with:
- Which script failed
- The error message
- The journal/category that triggered it (if applicable)

API-side failures (HTTP 429, timeouts) are often transient — the scripts log warnings and continue.

---

## Style

- Standard library only for core scripts (no new third-party dependencies)
- New functions follow the same doc/signature style as existing ones
- `profile.yaml` schema changes must be backward-compatible (new optional keys only)
