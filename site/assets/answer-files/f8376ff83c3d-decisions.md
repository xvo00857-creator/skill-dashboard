# Board Meeting Decisions — Layer 2

This file contains ONLY founder-approved decisions. Append-only. Decisions are never deleted — only superseded.
Managed by Chief of Staff after Phase 5. See `~/.claude/decisions/raw/` for full transcripts.

---

## 2026-02-15 — Spain Market Expansion

**Decision:** Expand to Spain in Q3 2026 with a pilot in Madrid and Barcelona.
**Owner:** CMO
**Deadline:** 2026-03-01
**Review:** 2026-04-01
**Rationale:** Market research shows 40% lower CAC than Germany. Two pilot customers already committed.

**User Override:** Founder reduced pilot scope from 5 cities to 2. Reason: reduce operational risk during expansion.

**Rejected:**
- Launch in all of Spain simultaneously — too resource-intensive at current headcount [DO_NOT_RESURFACE]
- Partner with a local distributor instead of direct sales — margins too low [DO_NOT_RESURFACE]

**Action Items:**
- [x] Hire Spanish-speaking CSM — Owner: CHRO — Completed: 2026-02-28 — Result: Hired Maria G., started 2026-03-10; retained through postmortem, role being redefined.
- [x] Finalize Madrid pilot customer contracts — Owner: CRO — Completed: 2026-08-10 — Result: Never finalized; pilot A entered procurement freeze, pilot B signed with a local competitor. Closed as failed; see 2026-08-10 postmortem.
- [x] Translate app to Spanish (ES-ES) — Owner: CTO — Completed: 2026-04-12 — Result: App shipped; sales collateral/pricing/demo not localized until 2026-06-20 (logged as execution deviation in 2026-08-10).

**Supersedes:**
**Superseded by:** 2026-08-10 (Spain Expansion Six-Month Postmortem — Pause Direct, Go Partner-Led)
**Raw transcript:** ~/.claude/decisions/raw/2026-02-15-spain-market-expansion.md

---

## 2026-02-28 — Pricing Strategy Revision

**Decision:** Move from per-seat to usage-based pricing effective Q2 2026.
**Owner:** CFO
**Deadline:** 2026-03-20
**Review:** 2026-05-01
**Rationale:** Usage-based aligns with customer value. Three enterprise customers requested it explicitly.

**User Override:**

**Rejected:**
- Freemium tier — not appropriate for enterprise healthcare segment [DO_NOT_RESURFACE]
- Raise prices 30% across the board — too aggressive without usage data [DO_NOT_RESURFACE]

**Action Items:**
- [ ] Model 3 pricing scenarios (conservative/base/aggressive) — Owner: CFO — Due: 2026-03-15 — Review: 2026-03-25
- [ ] Customer interviews on usage patterns (n=10) — Owner: CMO — Due: 2026-03-30 — Review: 2026-04-01
- [ ] Update billing infrastructure for usage tracking — Owner: CTO — Due: 2026-04-01 — Review: 2026-04-15

**Supersedes:**
**Superseded by:**
**Raw transcript:** ~/.claude/decisions/raw/2026-02-28-pricing-strategy-revision.md

---

## 2026-03-04 — Engineering Hiring Plan Q2

**Decision:** Hire 2 senior engineers in Q2: one ML/AI, one backend. No contractors.
**Owner:** CTO
**Deadline:** 2026-04-15
**Review:** 2026-05-01
**Rationale:** ML roadmap blocked. Backend capacity at 85%. Contractors rejected due to IP risk in regulated domain.

**User Override:** Founder added: "ML hire must have healthcare AI experience. Non-negotiable."

**Rejected:**
- Contract team of 5 for 3 months — IP risk in regulated domain [DO_NOT_RESURFACE]
- Hire junior engineers to save budget — wrong tradeoff at this stage [DO_NOT_RESURFACE]

**Action Items:**
- [ ] Post ML engineer JD — Owner: CHRO — Due: 2026-03-18 — Review: 2026-03-20
- [ ] Post backend engineer JD — Owner: CHRO — Due: 2026-03-18 — Review: 2026-03-20
- [ ] Define ML role requirements with healthcare AI spec — Owner: CTO — Due: 2026-03-17 — Review: 2026-03-15

**Supersedes:**
**Superseded by:**
**Raw transcript:** ~/.claude/decisions/raw/2026-03-04-engineering-hiring-q2.md

---

## 2026-08-10 — Spain Expansion Six-Month Postmortem (Pause Direct, Go Partner-Led)

**Decision:** Pause direct Spain expansion effective immediately. Run a 6-month partner-led motion in Spain (Madrid + Barcelona) with a single authorized reseller/implementation partner; revisit direct re-entry in 2027-Q1 with actuals. Write Q3 2026 ES revenue forecast to zero.
**Owner:** CRO (partner motion) with CMO (brand/presence) as co-owner; CFO owns forecast write-down.
**Deadline:** 2026-09-30
**Review:** 2026-11-15
**Rationale:** Actuals through 2026-08-07 show ES CAC ~65% above Germany (opposite of the Feb 15 prediction of 40% below), both "committed" pilots failed to convert, and pipeline coverage sat at 0.7x vs. plan ≥3x. Direct motion is under-resourced (no dedicated ES AE) and a local competitor now out-prices us; a partner-led 6-month test caps downside while generating real signed-deal data.

**User Override:** Founder explicitly reopened the 2026-02-15 "local distributor/partner" item that was marked DO_NOT_RESURFACE, stating: "reopen partner/distributor topic from 2026-02-15 — new information is that direct motion failed; revisit with updated margin math." Founder declined full Spain exit (keep brand presence, keep Maria G.) and declined sandbagging the forecast (write to zero, not partial).

**Rejected:**
- Full exit from Spain / write off the market — forfeits brand and a hired, ramped CSM for no learning [DO_NOT_RESURFACE]
- Continue direct motion as-is through Q3 "to give it more time" — no gating metric would change; throwing good money after bad [DO_NOT_RESURFACE]
- Re-forecast Q3 ES at partial (€100–200k) to soften the miss — hides the signal from the board and from planning [DO_NOT_RESURFACE]
- Reopen 5-city Spain rollout that founder cut on Feb 15 — failure was in the 2 cities, not the count [DO_NOT_RESURFACE]

**Action Items:**
- [ ] Sign one authorized ES reseller/implementation partner (term sheet + margin schedule) — Owner: CRO — Due: 2026-09-30 — Review: 2026-10-15
- [ ] Write Q3 2026 ES revenue forecast to zero in the board pack and reissue; tag the ~€420k plan as superseded — Owner: CFO — Due: 2026-08-20 — Review: 2026-08-25
- [ ] Define partner shortlist criteria and a target list of 5 ES partners — Owner: CRO — Due: 2026-08-24 — Review: 2026-08-31
- [ ] Re-baseline CAC methodology: n≥30 signed contracts (not LOIs), third-party source where possible, confidence intervals reported — Owner: CFO with CMO — Due: 2026-09-15 — Review: 2026-09-30
- [ ] Update CRM/pipeline definitions: only signed contracts count as "committed"; LOIs move to a separate "intent" stage — Owner: CRO — Due: 2026-09-01 — Review: 2026-09-15
- [ ] Add a mandatory Day-45 gating review to every new market entry with pre-agreed kill/continue criteria — Owner: Chief of Staff with CMO — Due: 2026-09-30 — Review: 2026-10-15
- [ ] Wire Review dates to auto-escalate: any decision whose review date passes with no written check-in is flagged in /cs:review — Owner: Chief of Staff — Due: 2026-09-15 — Review: 2026-09-30
- [ ] Localize sales enablement (collateral, pricing page, demo env) before app translation ships in future rollouts — Owner: CMO with CTO — Due: 2026-09-30 — Review: 2026-10-15
- [ ] Decide Maria G.'s role during the partner-led phase (partner-enablement lead vs. redeploy) — Owner: CHRO with CMO — Due: 2026-09-07 — Review: 2026-09-15
- [ ] Recommend accounting treatment of capitalized ES localization costs (write off vs. amortize) — Owner: CFO — Due: 2026-08-31 — Review: 2026-09-07

**Supersedes:** 2026-02-15
**Superseded by:**
**Raw transcript:** ~/.claude/decisions/raw/2026-08-10-spain-expansion-postmortem.md
