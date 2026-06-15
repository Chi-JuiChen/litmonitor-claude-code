# LitMonitor with Claude Code

Stay current with academic literature — Claude Code reads recent papers and scores each one for relevance to your research.

**Requires a Claude Code subscription (Pro plan or Team plan).** Paper scoring runs inside your active Claude Code session, so there are no separate API calls and no extra charges on top of your existing subscription.

> Inspired by [LitMonitor Earth](https://github.com/eabarnes1010/litmonitor) by Elizabeth A. Barnes (CC BY 4.0).

---

## How it works

1. A Python script fetches recent papers from journals and arXiv (free APIs — OpenAlex, Semantic Scholar)
2. Claude Code reads the papers and scores each one 1–10 based on your research profile
3. Results appear as a ranked table in the chat window

Papers you've already seen are cached, so only new ones are scored on each run.

---

## For Humans

This tool is designed to be used through Claude Code in plain English — you don't run any commands yourself. Claude Code handles everything behind the scenes.

### Getting started

Open Claude Code in your working directory, then say:

> "Clone https://github.com/Chi-JuiChen/litmonitor-claude-code and set it up in a subfolder called `litmonitor`"

Claude will clone the repository, open the project, read the setup instructions, and guide you through a short configuration interview — asking about your research field, topics, journals, and authors. At the end it writes your personal `profile.yaml`.

### Fetching and scoring papers

Once set up, say:

> "Fetch and score my papers"

Claude fetches recent papers, scores them in-session, and displays a ranked list. That's the whole workflow.

### Other things you can say

| Say this to Claude Code | What happens |
|---|---|
| "Setup" | Re-runs the profile configuration wizard |
| "Show papers scoring 7 or above" | Filters the results by score |
| "Fetch the last 30 days" | Extends the fetch window |
| "Update my profile" | Claude walks you through editing your research interests |
| "Add journal [name]" | Claude looks up the journal ID and adds it to your profile |
| "Re-score [paper title]" | Removes the cached score and re-evaluates that paper |

### Team use

Each team member opens their own Claude Code session, navigates to their working directory, and says the same clone command. Because `profile.yaml` is personal and never committed, everyone gets their own research profile from the same shared codebase.

---

## For Claude Code

> This section is a technical reference for Claude Code, not for human readers.

The complete setup wizard, 7-step fetch-and-score workflow, and scoring rules are in [`CLAUDE.md`](CLAUDE.md). Read it before acting on any user request.

### File reference

| File | Purpose |
|---|---|
| `CLAUDE.md` | Full workflow and scoring instructions for Claude Code |
| `fetch_papers.py` | Fetches papers from OpenAlex + arXiv; enriches abstracts via Semantic Scholar; writes `papers_raw.json` |
| `update_cache.py` | Reads `papers_scored.json` → persists new scores to `score_cache.json` |
| `show_results.py` | Renders `papers_scored.json` as a markdown table sorted by score |
| `profile.yaml` | Per-user research profile (gitignored; created by setup wizard) |
| `profile.template.yaml` | Blank starter template |
| `profiles/` | Field-specific templates: `atmospheric_science`, `oceanography`, `earth_system`, `ml_climate` |
| `papers_raw.json` | Auto-generated; `cached=false` entries need scoring |
| `papers_scored.json` | Auto-generated; all entries have scores filled in |
| `score_cache.json` | Cumulative score history; prevents re-scoring seen papers |

### Workflow summary

```
python fetch_papers.py    →  papers_raw.json  (cached=false entries need scoring)
Claude reads + scores     →  papers_scored.json
python update_cache.py    →  score_cache.json  (persists new scores)
python show_results.py    →  markdown table in chat
```

### Adding a new data source

Add `fetch_<source>(...)` to `fetch_papers.py` returning paper dicts with fields:
`paper_id`, `title`, `authors`, `abstract`, `journal`, `date`, `url`, `source`.
Call it from `main()` and accumulate into `all_papers`. See `CLAUDE.md` for the full schema.

---

## Abstract coverage for paywalled journals

- **OpenAlex** returns abstracts for most open-access papers
- **Semantic Scholar** fills gaps for paywalled publishers (AMS, Nature, AAAS) via separate licensing agreements — called automatically, no account needed
- Papers with no recoverable abstract are scored on title alone

---

## Attribution

This project is a reimplementation and extension of **[LitMonitor Earth](https://github.com/eabarnes1010/litmonitor)** by **Elizabeth A. Barnes**, licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).

Key differences from the original:
- Reimplemented in Python (the original is a standalone browser app)
- Scoring is done by Claude Code in-session rather than via direct API calls
- Added a guided setup wizard, score caching, field-specific profile templates, and CLI tools

## License

Released under the [MIT License](LICENSE). Credit is given to Elizabeth A. Barnes and [LitMonitor Earth](https://github.com/eabarnes1010/litmonitor) per the CC BY 4.0 terms of the original work.
