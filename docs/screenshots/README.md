# README screenshots

Upload **3 PNG files** here (crop sensitive cells in Excel first if needed):

| Filename | Excel sheet | What to show |
|---|---|---|
| `call-log.png` | CALL_LOG | Header row + ~10–15 scored calls (KPI columns, star rating, QA notes) |
| `agent-evaluations.png` | AGENT_EVALUATIONS | Per-agent rollup + training recommendations |
| `escalations.png` | ESCALATIONS | Any behavioral flags (or empty sheet with headers if none) |

**Tips**
- Freeze header row before screenshot
- Hide or blur agent names / phone numbers if you prefer
- Use the same workbook export for all three (one cohort run)

Optional: `scripts/generate_readme_screenshots.py` can auto-generate sanitized PNGs from an `.xlsx` if you prefer.
