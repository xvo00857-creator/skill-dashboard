# The Weekly SEO Ops Loop

A recurring loop for a B2B SaaS with a content-heavy site. Every Monday morning it
scans organic search signals and tells you what to do this week: new keyword gaps
to brief, ranking drops to fix, and internal-link edits to ship. It adapts three
catalog loops — **keyword-gap**, **ranking-drop watch**, and **internal-linking** —
into one weekly briefing, with a monthly **content-decay** pass noted as a
companion (add later, per the "one at a time" rule).

All actions are **Tier 1 (analysis + staged drafts)**. The loop never publishes,
never edits live pages, never changes site settings — it stages briefs and a
one-page action list for a human to approve and ship.

---

- **Check cadence**: Weekly, Monday 09:00 Asia/Singapore (`0 9 * * 1`).
  Rankings, backlinks, and domain authority move on a weekly rhythm; daily checks
  are noise (see the cadence rule).
- **Acts when**: At least one signal below is both (a) net-new vs. prior runs and
  (b) clears a minimum-impression threshold. Most runs should produce a short list;
  quiet weeks legitimately produce "stable — no action."
- **Purpose**: Protect and grow organic traffic on a content-heavy B2B SaaS site —
  catch regressions early, surface new ranking opportunities before competitors,
  and make sure new/pillar content gets the internal links it needs to rank.
- **Skills used**: `seo-audit` (rankings, GSC diffs, on-page), `analytics`
  (traffic/impressions, SERP-feature changes), `content-strategy` (briefs),
  `site-architecture` (internal links).
- **Loop body**:
  1. **Pull data.** From Google Search Console (performance + coverage), the rank
     tracker for priority keywords/pages, and the CMS for pages published/updated
     in the last 14 days. Window: trailing 7 days vs. prior 7 days AND vs. the same
     7 days last month (to absorb week-of-month seasonality).
  2. **Signal A — Keyword gaps.** Find striking-distance keywords (positions 5–20)
     with rising impressions, and rising queries that have no matching page.
     Classify each as: quick on-page win / net-new page / programmatic-template
     candidate. Keep up to 3 that clear the impression floor.
  3. **Signal B — Ranking drops.** For the priority keyword/page set, flag any
     page/keyword down ≥5 positions vs. its 4-week baseline, or any money/pillar
     page down ≥3. Diff what changed on and off the page (content edits, lost
     links, SERP-layout change, algo-update timing, coverage/indexing issues).
  4. **Signal C — Internal links.** For pages published/updated in the last 14
     days, find 2–4 relevant existing pages that should link *to* them (and vice
     versa), with specific anchor text. Skip forced/topically-unrelated links.
  5. **Self-check (before writing anything up).**
  6. **Stage output.** Draft up to 3 content briefs (Signal A), a regression
     diagnosis + fix per real drop (Signal B), and a link-edit list (Signal C).
     Write the one-page weekly briefing (see Output).
  7. **Update state.** Append to `handled`/`in_flight`, advance `cursor`, log the
     run.
- **Self-check** (verify before acting — don't act on noise):
  - **Movement vs. seasonality?** Compare to the same period last month, not just
    last week. A Monday-vs-Monday dip around a holiday/weekend is not a regression.
  - **SERP-feature change or volatility?** If a SERP layout changed (new featured
    snippet, people-also-ask, video carousel) or rankings are swinging broadly,
    note it as a SERP shift, not a page loss — don't mass-edit.
  - **Tracking/indexing real?** Cross-check GSC coverage: a "drop" that coincides
    with a deindex, noindex tag, canonical flip, or tracking break is a technical
    bug, not a content problem.
  - **Sample size.** Don't brief a gap below the impression floor (default:
    ≥~200 impressions/week for the query, or a clear rising trend for 2+ weeks).
    Don't diagnose a drop on a keyword with <~50 clicks/week as a content issue —
    it's likely noise.
  - **Link relevance.** Each internal link must be contextually relevant; skip
    link-stuffing and forced anchors.
- **State / idempotency** (file: `.agents/loops/weekly-seo-ops.json`):
  - `cursor` — high-water timestamp of data processed; only act on items newer.
  - `handled.keyword_gaps` — query strings already briefed; don't re-brief an open
    one (re-surface only if it materially changes position band or intent).
  - `handled.rank_drops` — page/keyword keys already filed as open issues; update
    the existing issue rather than re-filing.
  - `handled.link_pairs` — `(source→target)` pairs already linked; never suggest a
    duplicate.
  - `in_flight` — open briefs/drops currently being worked; don't pile on.
  - `cooldowns` — per-page cooldown after a content refresh (default 60 days) so a
    freshly-refreshed page isn't re-queued.
  - First run sets `cursor` to "now" (no historical backfill); do a dry run before
    acting on any backlog.
- **Stop / bail-out**:
  - No item clears thresholds → log `checked=N acted=0 note="stable — no action"`
    and send a one-line "all clear" briefing. This is the expected common case.
  - **Data-source outage or stale data** (GSC/rank tracker down, coverage errors,
    tracking break) → report "stale data — skipping action" with the specific
    source. **Never fabricate movement** from partial data.
  - **Suspected algorithm update** (broad cross-site swings, known-update timing)
    → escalate to a human with the evidence; do not mass-edit pages.
  - **Tier-2 guardrail**: the loop only stages drafts and link suggestions. A human
    approves before any publish, live page edit, redirect, noindex, or site-setting
    change. No spend, no send, no publish in this loop.
  - **Error path**: on an unexpected error, log it, leave state untouched, and
    surface the error in the briefing rather than silently skipping.
  - **Kill switch**: disable the cron job (or set `enable:false`) to stop the loop
    immediately; state is preserved so it can resume cleanly.
- **Output**: A dated one-page briefing at
  `.agents/loops/briefings/YYYY-MM-DD-seo-weekly.md` plus a notification, containing:
  - **Headline**: organic sessions WoW + MoM, and whether the week is "stable,"
    "action items," or "escalate."
  - **This week's actions (ranked)**: up to 3 content briefs (keyword, intent,
    recommended format, target position band), regression fixes (page, likely
    cause, proposed fix), and internal-link inserts (source → target, anchor).
  - **No-action / escalations**: what was checked and dismissed, and anything
    needing a human decision (suspected algo hit, tracking issue).
  - **Run log line** appended to `.agents/loops/weekly-seo-ops.log`.

---

## Monthly companion (do NOT build yet — one loop at a time)

After this weekly loop has run 3–4 cycles and is earning its keep, add **The
content-decay loop** (monthly, trailing-90-day traffic/rank decline → refresh
plans). It shares the same state file and Tier-2 guardrail. Per the orchestration
rollout, prove the weekly loop first, then add the monthly pass.

## First-run checklist

- [ ] Confirm priority keyword/page set and impression floor (defaults above).
- [ ] Confirm data sources: GSC property, rank tracker, CMS.
- [ ] Initialize `.agents/loops/weekly-seo-ops.json` with `cursor = now`.
- [ ] Dry run: log what it *would* do, act on nothing.
- [ ] Then enable the weekly cron.
- [ ] After 3–4 cycles, ask: is anyone acting on the output? If not, kill it
      before it becomes a vanity loop.
