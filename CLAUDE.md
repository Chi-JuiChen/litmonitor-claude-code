# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this tool does

LitMonitor Claude fetches recent academic papers from OpenAlex (journals) and arXiv, enriches missing abstracts via Semantic Scholar, and uses Claude Code itself (in-session) to score each paper 1–10 based on a user-defined research profile. No separate Anthropic API key is needed — scoring happens within the current Claude Code session at no extra cost.

## First-time setup wizard

**Check for profile.yaml first.** If `profile.yaml` does not exist in the project root, run the setup wizard before anything else.

### Setup wizard instructions

Tell the user: "Welcome to LitMonitor Claude! I'll ask you a few questions to set up your research profile. This only needs to be done once."

Ask the following questions **one at a time**, waiting for each answer:

1. **Name and email**
   "What's your name and email address? (Your email is used in API request headers for OpenAlex's polite pool — it's never stored or shared.)"

2. **Research field** — offer these options:
   - Atmospheric / climate science
   - Oceanography
   - Earth system science (broad)
   - ML / AI applied to climate and weather
   - Other (I'll describe my own)

   Based on the answer, load the matching template from `profiles/` as the starting point.

3. **Research context**
   "In 1–2 sentences, describe your research role and focus. Example: 'I am a postdoc studying subseasonal precipitation predictability using machine learning.'"

4. **Topics to prioritize (score 8–10)**
   "What are your main research topics? List them one per line. Papers that match these will score 8–10."

5. **Transferable methods (score 8–10)**
   "Are there methods from outside your field that you'd want to apply to your work? These also score 8–10. Examples:
   - uncertainty quantification
   - OOD (out-of-distribution) detection
   - probabilistic forecasting
   - spatial/temporal deep learning methods
   Leave blank if none."

6. **Topics to downgrade (score 1–4)**
   "Are there topics you want to filter out or deprioritize? These will score 1–4. Examples:
   - purely observational studies (no modeling)
   - standard NWP without novel AI components
   - topics unrelated to your region or variable of interest
   Leave blank if none."

7. **Priority authors**
   "Any specific researchers whose papers you always want to see, regardless of topic? List one name per line as 'Last, F.' — they'll always score 8–10. Leave blank if none."

8. **Journals** — show the default list from the chosen template and ask:
   "Here are the default journals for your field: [list]. Do you want to add or remove any? You can also do this later by editing profile.yaml."

9. **arXiv categories** — show defaults and ask:
   "Default arXiv categories: [list]. Any changes?"

10. **Days back**
    "How many days back should each fetch go? Default is 14."

After collecting answers, write `profile.yaml` using the template as a base, filled in with the user's answers. Then confirm: "Your profile is saved to profile.yaml. Run `python fetch_papers.py` to fetch your first batch of papers."

---

## Fetch-and-score workflow

When the user says "fetch papers", "score papers", "fetch and score", or similar:

### Step 1 — Fetch
```
python fetch_papers.py
```
This writes `papers_raw.json`. Papers already in `score_cache.json` have `"cached": true` with scores pre-filled.

### Step 2 — Identify papers to score
Read `papers_raw.json`. Find all papers where `"cached": false` — these need scoring. Papers with `"cached": true` already have scores; copy them unchanged.

### Step 3 — Read the research profile
Read `profile.yaml`. Extract:
- `prioritize` — topics that earn 8–10
- `transferable_methods` — also earns 8–10
- `downgrade` — earns 1–4
- `priority_authors` — always earns 8–10 regardless of topic

### Step 4 — Score each paper

For each paper where `"cached": false`:

**Scoring rules:**
- **8–10**: Strong match to `prioritize` or `transferable_methods`, OR any author fuzzy-matches a `priority_authors` entry (last name + first initial, case-insensitive)
- **5–7**: Peripheral or indirect relevance
- **1–4**: Matches `downgrade`, or no meaningful connection

**Priority author check:** Compare each author in `authors` (comma-separated) against every entry in `priority_authors`. Match on last name + first initial. If any author matches, score 8–10 regardless of topic.

**Missing abstract:** Score on title alone; note this in the reason.

**Output per paper:**
- `score`: integer 1–10
- `reason`: one sentence, ≤ 20 words, explaining the score
- `scored_at`: current UTC timestamp in format `YYYY-MM-DDTHH:MM:SSZ`

### Step 5 — Write papers_scored.json
Write the complete `papers_scored.json` with the same top-level structure as `papers_raw.json`:
```json
{
  "metadata": { ...same as papers_raw.json... },
  "papers": [ ...all papers, every score filled in... ]
}
```
All papers must be present (both cached and newly scored). Cached papers are copied verbatim.

### Step 6 — Update cache
```
python update_cache.py
```

### Step 7 — Display results
```
python show_results.py
```
Display the output as a markdown table in the chat.

---

## Scoring tips

- Use semantic judgment, not exact keyword matching. A paper on "graph neural networks for fluid dynamics" matches "CNNs for spatial data" as a transferable method.
- Short, vague abstracts are common for new arXiv preprints. If `abstract` contains "(no abstract)", score on title alone and note it.
- When in doubt between two scores, prefer the higher one for borderline cases involving the `prioritize` topics.

---

## Other commands

| User says | Action |
|---|---|
| "setup" or "first-time setup" | Run the setup wizard above |
| "show results" | Run `python show_results.py` and display output |
| "show high-scoring papers" | Run `python show_results.py --min-score 8` |
| "fetch last 30 days" | Run `python fetch_papers.py --days 30` |
| "re-score all papers" | Run `python fetch_papers.py --force`, then score all |
| "update my profile" | Read profile.yaml, show current values, ask what to change, rewrite the file |
| "add journal X" | Look up the OpenAlex source ID for X, append to journals in profile.yaml |
| "re-score paper <title>" | Find its paper_id in score_cache.json, delete that entry, re-run fetch, score just that paper |

---

## File reference

| File | Purpose |
|---|---|
| `profile.yaml` | Your research profile (gitignored, per-user) |
| `papers_raw.json` | Fetched papers; `cached=false` ones need scoring (gitignored) |
| `papers_scored.json` | All papers with scores filled in (gitignored) |
| `score_cache.json` | Cumulative score history (gitignored) |
| `fetch_papers.py` | Fetches from OpenAlex + arXiv, enriches via Semantic Scholar |
| `update_cache.py` | Persists new scores to score_cache.json |
| `show_results.py` | Renders scored papers as markdown |
| `profiles/` | Field-specific profile templates for new users |
| `profile.template.yaml` | Blank starter template |

---

## Adding a new data source

Add a function `fetch_<source>(...)` to `fetch_papers.py` that returns a list of paper dicts with these required fields:
```python
{
    "paper_id": str,   # stable unique ID, e.g. "doi:10.xxx" or "arxiv:2606.xxx"
    "title":    str,
    "authors":  str,   # comma-separated names
    "abstract": str,   # empty string if unavailable
    "journal":  str,
    "date":     str,   # YYYY-MM-DD
    "url":      str,
    "source":   str,   # short source name, e.g. "crossref"
}
```
Then call it from `main()` and add the results to `all_papers`.
