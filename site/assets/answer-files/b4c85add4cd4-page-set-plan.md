# Competitor Page Set Plan

Companion to `asana-alternatives.md`. Per the competitors Skill Output Format,
this recommends additional pages to create, prioritized by likely search volume
and conversion intent for a small-team, price + simplicity positioned PM tool.

All pages pull from the centralized YAML in `competitor_data/`. Update data
there once; it propagates to every page.

## Priority order

| # | Page | Format | URL | Target keyword | Priority | Why |
|---|---|---|---|---|---|---|
| 1 | **Best Asana Alternatives** (this page) | Plural alternatives | `/alternatives/asana-alternatives` | "asana alternatives" | 🔴 P0 — done | High volume; top-of-funnel; captures researchers |
| 2 | [Your Product] vs Asana | You vs competitor | `/vs/asana` | "[your product] vs asana" | 🔴 P0 | Highest conversion intent — evaluators comparing directly |
| 3 | Asana Alternative (singular) | Singular alternative | `/alternatives/asana` | "asana alternative" | 🟠 P1 | Strong switcher intent; "switch from Asana" long-tail |
| 4 | Best ClickUp Alternatives | Plural alternatives | `/alternatives/clickup-alternatives` | "clickup alternatives" | 🟠 P1 | ClickUp is the price-adjacent competitor; capture "too complex" switchers |
| 5 | Best monday.com Alternatives | Plural alternatives | `/alternatives/monday-alternatives` | "monday alternatives" | 🟡 P2 | High volume; monday users also hit feature-gating pain |
| 6 | Best Trello Alternatives | Plural alternatives | `/alternatives/trello-alternatives` | "trello alternatives" | 🟡 P2 | Trello teams outgrowing Kanban are ideal [Your Product] leads |
| 7 | [Your Product] vs ClickUp | You vs competitor | `/vs/clickup` | "[your product] vs clickup" | 🟡 P2 | Direct comparison with the price-adjacent rival |
| 8 | Best Basecamp Alternatives | Plural alternatives | `/alternatives/basecamp-alternatives` | "basecamp alternatives" | 🟢 P3 | Shared simplicity positioning; differentiate on price + features |
| 9 | Best Notion Alternatives | Plural alternatives | `/alternatives/notion-alternatives` | "notion alternatives" | 🟢 P3 | Capture doc-first teams realizing they need real PM |
| 10 | Asana vs ClickUp | Competitor vs competitor | `/compare/asana-vs-clickup` | "asana vs clickup" | 🟢 P3 | Third-party comparison traffic; introduce [Your Product] as option 3 |
| 11 | Alternatives index | Index | `/alternatives` | (hub) | 🟠 P1 with P0 pages | Hub linking all alternative pages; passes link equity |
| 12 | Comparisons index | Index | `/vs` | (hub) | 🟡 P2 with P0/P1 vs pages | Hub for all head-to-head pages |

## Internal linking notes

- Every page links back to its index (`/alternatives` or `/vs`) and cross-links
  to 2–3 related comparisons (e.g., the Asana alternatives page links to
  [Your Product] vs Asana and Asana vs ClickUp).
- Add footer columns per the Skill's content-architecture guidance:
  - "[Your Product] vs" → vs Asana, vs ClickUp, vs monday.com
  - "Alternatives to" → Asana, ClickUp, monday.com, Trello
  - "Compare" → Asana vs ClickUp, Asana vs monday.com
- Add "Last updated" date to each page for credibility.

## Data maintenance cadence

- **Quarterly:** Verify pricing and major feature changes for each competitor.
- **On customer signal:** Update when a customer mentions a competitor change.
- **Annually:** Full refresh of all competitor data and review themes.

## Open items to confirm with the team

- [Your Product] official name and domain (replace placeholders)
- Exact free-tier limits and any higher-tier plan
- Migration tooling details (importer? white-glove for 10+ seats?)
- Real customer testimonials for the social proof sections
- Support SLA / onboarding details for the service comparison
- Integrations list (to populate the integrations row accurately)
