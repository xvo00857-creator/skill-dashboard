# Lead Lifecycle Stages — Mid-Market B2B SaaS (HubSpot)

> **Purpose:** Align marketing and sales on shared lead definitions, scoring, routing, and SLAs so every lead is worked the same way and handoffs don't leak pipeline.
>
> **Assumptions (adjust to fit):** ACV ~$5K–$25K · sales-led or hybrid motion · sales cycle 30–90 days · HubSpot Professional/Enterprise as system of record · SDR + AE sales team.

---

## 1. The Alignment Problem in One Sentence

If marketing calls something an MQL but sales won't work it, **the definition is wrong** — not the lead. This document is the single source of truth both teams sign off on. Get alignment on paper before building any HubSpot workflows.

---

## 2. Lifecycle Stage Definitions

Use HubSpot's default `Lifecycle Stage` property. Set it via workflow — never let reps edit it manually except to move SQL → Opportunity (which they do by creating a deal).

| Stage | Entry Criteria | Exit Criteria | Owner | HubSpot Property Value |
|-------|---------------|---------------|-------|----------------------|
| **Subscriber** | Opts in to blog/newsletter/content; no company info required | Provides company info via form, enrichment, or 3+ page sessions in one visit | Marketing (automated) | `Subscriber` |
| **Lead** | Identified contact with name + email + company (form fill, import, or enrichment) | Reaches MQL threshold (fit **and** engagement) OR manually qualified by SDR | Marketing | `Lead` |
| **MQL** | Fit score ≥ 30 **AND** engagement score ≥ 30 (see §3), OR triggers a high-intent action (demo request, Contact Sales form) | Sales accepts → SQL; sales rejects → Recycled (with reason code); no action in 48 hrs → escalated | Marketing → Sales (handoff) | `Marketing Qualified Lead` |
| **SQL** | Rep has a live conversation and confirms ≥2 of BANT (Budget, Authority, Need, Timeline) | Opportunity created with deal value + close date; or disqualified with reason code | Sales (SDR or AE) | `Sales Qualified Lead` |
| **Opportunity** | Deal created in HubSpot with value, close date, and pipeline stage | Closed-won or closed-lost | Sales (AE) | `Opportunity` |
| **Customer** | Deal stage = Closed Won; contract signed | Expands, renews, or churns | Customer Success | `Customer` |
| **Evangelist** | NPS 9–10, referral activity, or agrees to case study | Ongoing program participation | CS + Marketing | `Evangelist` (custom) |
| **Recycled** | Sales rejects MQL/SQL with a reason code | Re-engages and re-crosses MQL threshold → re-routes as Recycled MQL | Marketing (nurture) | `Other` + custom `Recycled Lead Status` |

### The MQL rule that fixes alignment

> **An MQL requires BOTH fit AND engagement. Neither alone is enough.**
> A perfect-fit company that never visits your pricing page or requests a demo is *not* an MQL. A student downloading every whitepaper is *not* an MQL. This single rule eliminates 80% of marketing/sales arguments.

---

## 3. Lead Scoring Specification (Mid-Market Balanced Model)

**Weighting: 50% fit / 50% engagement.** Configure in HubSpot → Settings → Properties → `HubSpot Score`. Use positive and negative attributes.

### Fit Score (target ≥ 30 of 50)

| Attribute | Criteria | Points |
|-----------|----------|--------|
| Company size | 50–1000 employees | +15 |
| | 1000+ (if you sell upmarket) | +10 |
| | < 20 employees | 0 |
| Industry | Primary target vertical(s) | +10 |
| | Secondary vertical | +5 |
| Job title / seniority | Manager, Director, VP, C-level | +15 |
| | Individual contributor | +5 |
| Geography | Primary market | +10 |
| | Secondary market | +5 |
| Tech stack | Uses a complementary/integration tool | +10 |
| | Uses a competitor you replace | +10 |

### Engagement Score (target ≥ 30 of 50)

| Signal | Points | Decay |
|--------|--------|-------|
| Demo request / Contact Sales form | +30 | None |
| Free trial signup | +25 | None |
| Pricing page visit | +15 | −5/week |
| Case study / comparison page (2+) | +15 | −5/2 weeks |
| Webinar attendance | +10 | −5/month |
| Content download (2nd+ gated asset) | +10 | −5/month |
| Email click (3+) | +10 | −2/month |
| Blog visits (5+ pages) | +10 | −5/2 weeks |

### Negative Score (apply to total)

| Signal | Points |
|--------|--------|
| Competitor email domain | −50 |
| Student/intern title or .edu | −25 |
| Personal email (gmail/yahoo) | −10 |
| Hard bounce / spam complaint | −50 / −100 |
| Unsubscribe | −20 |
| Careers-page-only visitor | −30 |
| No site visit in 90 days | −15 |

### MQL threshold

**Total score ≥ 60** (fit ≥ 30 AND engagement ≥ 30), OR a high-intent action (demo request/Contact Sales) from a contact with fit ≥ 20.

**Calibration:** Quarterly. Pull closed-won deals from the last 6–12 months, retroactively score them, and confirm the threshold catches ≥80% of wins while not flooding sales with closed-lost lookalikes.

---

## 4. MQL → SQL Handoff SLA

This is where misalignment turns into lost revenue. Document it, automate it, report on it weekly.

| Step | Target | Escalation if missed |
|------|--------|---------------------|
| First contact attempt (call/email) | Within **4 business hours** of MQL creation | Alert sales manager at 4 hrs |
| Qualification decision (accept/reject) | Within **48 hours** | Auto-escalate to manager; reassign if no action |
| Discovery meeting scheduled (if accepted) | Within **5 business days** | Flag in weekly pipeline review |
| Rejected MQL | Must include a reason code (see §5) | Moves to Recycled immediately |

**Speed-to-lead note:** Industry data shows contacting within 5 minutes makes a lead 21× more likely to qualify; after 30 minutes conversion drops 10×; after 24 hours the lead is effectively cold. The 4-hour SLA is a *floor* — aim for under 5 minutes on demo requests via instant alerts.

---

## 5. Rejection Reason Codes & Recycling

When sales rejects an MQL, they **must** pick a reason. This is non-negotiable — it's how marketing learns and how you measure lead quality.

| Code | Reason | Recycle Action |
|------|--------|----------------|
| FIT-01 | Company too small | Nurture; re-score if company grows |
| FIT-02 | Wrong industry | Archive; do not recycle |
| FIT-03 | Wrong role / no authority | Nurture; monitor for job changes |
| ENG-01 | No response after 3 attempts | Recycle to nurture; re-evaluate in 90 days |
| ENG-02 | Interested, bad timing | Nurture; re-engage in 60 days |
| QUAL-01 | No budget this cycle | Nurture; re-engage in 90 days |
| QUAL-02 | Locked into competitor | Recycle; trigger before their renewal date |
| QUAL-03 | Not a real project | Archive; do not recycle |

**Recycling workflow:** Rejected → lifecycle = Recycled → engagement score resets to baseline (keep fit score) → enters a lower-frequency nurture (bi-weekly/monthly, industry content + case studies) for 6 months → if they re-engage and cross MQL threshold, re-route to sales flagged as "Recycled MQL." Track recycled-MQL conversion separately.

---

## 6. Lead Routing Rules (HubSpot)

**Principle:** Route to the most specific match first; always have a fallback owner so no lead goes cold.

```
New MQL arrives
│
├─ From a named/target account?  → assigned account owner
├─ Company size > 1000?          → enterprise/mid-market AE pool
├─ Matches a territory (geo/vertical)? → territory owner
└─ Default                       → round-robin across eligible reps
                                   └─ No rep available? → team queue, 1-hr SLA
```

**Round-robin rules:**
- Skip reps on PTO, at capacity, or with full pipeline.
- Weight lightly toward reps below quota.
- Reset distribution weekly.
- Log every assignment (HubSpot does this natively via workflow history).

**HubSpot setup:** Automation → Workflows → trigger on `Lifecycle Stage = MQL` → action "Rotate contact owner" among your sales user list → create follow-up task due in 4 hours → send internal email + Slack notification with lead context (recent page views, downloads, score breakdown).

---

## 7. HubSpot Automation Workflows to Build

Build these in order. Each references the one before it.

| # | Workflow | Trigger | Key Actions |
|---|----------|---------|-------------|
| 1 | **Auto-MQL on score** | `HubSpot Score ≥ 60` (with fit ≥ 30 AND engagement ≥ 30) | Set lifecycle = MQL, set MQL Date, suppress from nurture, trigger #2 |
| 2 | **MQL alert & assignment** | Lifecycle becomes MQL | Rotate owner, send alert email + Slack, create 4-hr task, enroll in follow-up sequence |
| 3 | **SLA escalation** | Lifecycle = MQL AND no contact in 12 hrs | Warn owner → 24 hrs alert manager → 48 hrs reassign via rotation |
| 4 | **Meeting booked** | Meeting activity logged (Calendly/HubSpot Meetings) | Alert owner, prep task 1 hr before, if stage = Lead → set MQL, include activity context |
| 5 | **Recycled nurture** | Rejection reason code is known | Set stage = Recycled, reset engagement score, enroll in recycle nurture, set re-MQL trigger |
| 6 | **Closed-won → CS handoff** | Deal stage = Closed Won | Set contact = Customer, assign CS owner, create kickoff task, enroll in onboarding, remove from sales sequences |
| 7 | **Stale deal alert** | Days in stage > 2× average (Discovery 14d / Proposal 10d / Negotiation 21d) | Alert owner → 7 days alert manager → add to stale-deal list |
| 8 | **Daily activity digest** | Scheduled 8 AM daily | Email each owner their SQL/Opp contacts with site activity in last 24 hrs |

**Suppression lists to add across workflows:** existing customers, competitor domains, hard bounces, unsubscribes.

---

## 8. Pipeline (Deal Stage) Configuration

Separate from lifecycle stages — this is the sales process once an Opportunity exists.

| Deal Stage | Required Fields to Advance | Exit Criteria |
|-----------|---------------------------|---------------|
| **Qualified** | Contact info, company, lead source, fit score | Discovery call scheduled |
| **Discovery** | Pain points, current solution, timeline, BANT confirmed | Needs confirmed, demo scheduled |
| **Demo/Evaluation** | Technical requirements, decision-makers identified | Positive evaluation, proposal requested |
| **Proposal** | Pricing, terms, stakeholder map | Proposal delivered and reviewed |
| **Negotiation** | Redlines, approval chain, close date | Terms agreed, contract sent |
| **Closed Won** | Signed contract, payment terms | CS handoff complete |
| **Closed Lost** | Loss reason, competitor (if any) | Post-mortem logged |

**Pipeline hygiene automations:** required-field enforcement per stage, stale-deal alerts (#7), stage-skip detection (alert if Qualified → Proposal skips Discovery), close-date push reason required.

---

## 9. Metrics Dashboard Spec

Build three HubSpot dashboards. Review weekly at the RevOps/marketing-sales sync.

### Marketing view
| Metric | Definition | Target |
|--------|-----------|--------|
| Lead volume | New leads by source/week | Trend |
| Lead → MQL rate | MQLs ÷ total leads | 5–15% |
| Cost per MQL | Spend ÷ MQLs by channel | Trend down |
| Source attribution | MQLs/wins by first-touch source | — |

### Sales view
| Metric | Definition | Target |
|--------|-----------|--------|
| MQL → SQL acceptance | SQLs ÷ MQLs | 30–50% |
| SQL → Opportunity | Opportunities ÷ SQLs | 50–70% |
| Avg time in each stage | Days per deal stage | Flag 2× average |
| Speed-to-lead | Avg/median time MQL → first contact | < 5 min on demos; < 4 hrs general |
| SLA compliance | % MQLs contacted within 4 hrs | ≥ 90% |
| Win rate | Closed-won ÷ total opportunities | 20–30% |

### Executive view
| Metric | Definition | Target |
|--------|-----------|--------|
| Pipeline coverage | Open pipeline ÷ quota | 3–4× |
| CAC | Sales + marketing spend ÷ new customers | LTV:CAC ≥ 3:1 |
| LTV:CAC | Customer lifetime value ÷ CAC | 3:1–5:1 |
| Pipeline velocity | (# deals × avg size × win rate) ÷ sales cycle | Trend up |
| Recycled MQL conversion | Recycled → re-MQL → won | Track separately |

**Red flags to recalibrate:** MQL→SQL acceptance drops below 30%, sales consistently says "not ready," high-scoring leads don't convert, or MQL volume spikes without pipeline following.

---

## 10. Implementation Sequence

1. **Week 1 — Align on paper.** Walk marketing + sales through this doc. Agree on stage definitions, the MQL fit+engagement rule, reason codes, and SLAs. Sign-off from both VPs.
2. **Week 2 — Configure HubSpot.** Set up scoring properties, lifecycle stage options, custom reason-code property, required fields per deal stage.
3. **Week 3 — Build workflows 1–5** (MQL promotion through recycling). Test with internal fake leads.
4. **Week 4 — Build workflows 6–8** (CS handoff, stale deals, digest). Launch dashboards.
5. **Week 5 — Go live.** Announce the new definitions to both teams. Start the weekly marketing-sales SLA/metrics sync.
6. **Quarterly — Recalibrate.** Score historical wins/losses, adjust weights/thresholds, update reason codes based on what sales actually rejects.

---

## Open Inputs That Would Sharpen This

These weren't specified; the defaults above are reasonable mid-market assumptions. Swap in your real numbers:

- **Exact ACV range** — drives deal-desk thresholds and enterprise vs. mid-market routing split.
- **Sales cycle length** — tunes SLA windows and stale-deal thresholds.
- **Target industries/verticals** — populate the fit-score industry rows.
- **Current lead volume/month** — determines whether round-robin is enough or you need territory/skill routing.
- **Existing SDR/AE headcount and territories** — finalizes the routing tree.
- **Current tech stack** (marketing automation, enrichment, scheduling) — adds specific integration steps (Clearbit/Apollo enrichment, Calendly/SavvyCal routing).
