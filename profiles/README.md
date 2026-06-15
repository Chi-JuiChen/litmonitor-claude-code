# Profile Templates

Copy the template closest to your research area to `profile.yaml` in the project root, then customize it.

| Template | Best for |
|---|---|
| `atmospheric_science.yaml` | Atmospheric dynamics, weather prediction, S2S, precipitation |
| `oceanography.yaml` | Ocean circulation, sea level, marine biogeochemistry |
| `earth_system.yaml` | Carbon cycle, land-atmosphere coupling, tipping points |
| `ml_climate.yaml` | ML/AI methods applied to weather and climate |

**Quick start:**
```bash
cp profiles/atmospheric_science.yaml profile.yaml
# Then edit profile.yaml with your specific research interests
```

Or open the project in Claude Code and type **"setup"** — Claude will ask you questions and write `profile.yaml` for you.

---

## Adding a new template

1. Create `profiles/<field>.yaml` based on an existing template
2. Update this README table
3. Commit and submit a pull request — contributions welcome!

## Finding OpenAlex journal IDs

Visit: `https://api.openalex.org/sources?search=<journal+name>`

Look for the `id` field in the result, e.g. `"id": "https://openalex.org/S137773608"` → use `S137773608`.
