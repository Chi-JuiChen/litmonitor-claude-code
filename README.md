# LitMonitor with Claude Code

Stay current with academic literature using Claude Code as your AI-powered reviewer. **Requires a Claude Code subscription** — but if you already have one, paper scoring is included at no additional cost.

LitMonitor with Claude Code fetches recent papers from academic journals and arXiv, then uses your active Claude Code session to score each paper 1–10 based on your research interests. Scoring happens *inside* Claude Code, so there are no separate API calls and no extra charges beyond your existing Claude subscription.

> Inspired by [LitMonitor Earth](https://github.com/eabarnes1010/litmonitor) by Elizabeth A. Barnes (CC BY 4.0).

---

## How it works

1. **Python fetches papers** (free APIs: OpenAlex, arXiv, Semantic Scholar)
2. **Claude Code scores them** in-session using your research profile
3. **Results appear as a ranked markdown table** in the chat

Score caching means papers you've already seen aren't re-scored on future runs.

---

## Quickstart

### Requirements
- [Claude Code](https://claude.ai/code) with any subscription (Team plan works for shared use)
- Python 3.8+ (standard library only — no pip install needed)

### Setup

```bash
git clone https://github.com/YOUR_USERNAME/litmonitor-claude-code.git
cd litmonitor-claude-code
```

Open the folder in Claude Code, then type:

```
setup
```

Claude will ask you a series of questions about your research interests and write `profile.yaml` for you.

Alternatively, copy a template and edit manually:
```bash
cp profiles/atmospheric_science.yaml profile.yaml
# edit profile.yaml with your details
```

### Fetch and score papers

In Claude Code, type:
```
fetch and score papers
```

Claude runs the fetch script, scores the new papers in-session, and displays a ranked table.

---

## Workflow details

```
fetch_papers.py           # pulls from OpenAlex + arXiv, fills abstracts via Semantic Scholar
       ↓
papers_raw.json           # all papers; cached ones already have scores
       ↓
Claude scores in-session  # reads profile.yaml, assigns 1–10 + one-line reason
       ↓
papers_scored.json        # complete scored list
       ↓
update_cache.py           # persists new scores to score_cache.json
       ↓
show_results.py           # renders markdown table sorted by score
```

### Script flags

```bash
python fetch_papers.py --days 30     # fetch last 30 days instead of profile default
python fetch_papers.py --force       # ignore cache, re-score everything
python fetch_papers.py --no-enrich   # skip Semantic Scholar abstract enrichment

python show_results.py --min-score 7 # show only score ≥ 7
python show_results.py --json        # output raw JSON
```

---

## Research profile

`profile.yaml` (gitignored — yours alone) controls scoring:

| Section | Effect |
|---|---|
| `prioritize` | Topics that score 8–10 |
| `transferable_methods` | Methods from other fields — also score 8–10 |
| `downgrade` | Topics to suppress — score 1–4 |
| `priority_authors` | Specific researchers — always score 8–10 |
| `journals` | OpenAlex source IDs or ISSNs to monitor |
| `arxiv_categories` | arXiv categories to monitor |

---

## Profile templates

Pre-built templates in `profiles/` for common research areas. Copy one to `profile.yaml` to get started:

```bash
cp profiles/atmospheric_science.yaml profile.yaml
cp profiles/oceanography.yaml profile.yaml
cp profiles/earth_system.yaml profile.yaml
cp profiles/ml_climate.yaml profile.yaml
```

---

## Team / shared use

Each team member:
1. Clones the repo
2. Runs setup (`profile.yaml` is gitignored, so each person has their own)
3. Gets a personalized feed from the same journal list

To share a common journal list across the team, commit a team template to `profiles/` and have everyone copy it.

---

## Abstract coverage for paywalled journals

- **OpenAlex** returns abstracts for most open-access papers
- **Semantic Scholar** (called automatically) fills gaps for paywalled publishers like AMS, Nature, and AAAS via separate licensing agreements
- Papers with no recoverable abstract are scored on title alone

---

## Extending

### Add a journal
Append to `journals:` in `profile.yaml` — no code change needed:
```yaml
  - "My New Journal | S<OpenAlex-ID>"
```
Find the ID at: `https://api.openalex.org/sources?search=journal+name`

### Add a data source
See the "Adding a new data source" section in `CLAUDE.md`.

### Add a profile template
Create `profiles/<field>.yaml`, update `profiles/README.md`, and submit a pull request.

---

## Cost

| Component | Cost |
|---|---|
| Paper fetching (OpenAlex, arXiv, Semantic Scholar) | Free |
| Scoring by Claude Code | Included in your Claude Code subscription |
| Separate Anthropic API key | Not needed |

---

## Attribution

This project is a reimplementation and extension of **[LitMonitor Earth](https://github.com/eabarnes1010/litmonitor)** by **Elizabeth A. Barnes**, licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).

Key differences from the original:
- Reimplemented in Python (the original is a standalone HTML/JS browser app)
- Scoring is done by Claude Code in-session rather than via direct Anthropic API calls
- Added a guided setup wizard, score caching, field-specific profile templates, and CLI tools

## License

This project is released under the [MIT License](LICENSE). Per the CC BY 4.0 terms of the original work, credit is given to Elizabeth A. Barnes and the [LitMonitor Earth](https://github.com/eabarnes1010/litmonitor) project above.
