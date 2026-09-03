# Bookings Forecast — 3-Tier

**Profile:** `saas`  •  **Target period:** 2026-10-01 → 2026-12-31
**Opportunities scored:** 15

## Three numbers

| Tier | Amount | Notes |
|---|---:|---|
| **Commit** | $1,042,655 | Commit-grade stages × blended conversion × time-to-close × stall penalty |
| **Best-case** | $1,636,444 | Best-case stages × blended conversion × time-to-close |
| **Pipe-only** | $1,804,806 | All pipeline × blended conversion (no time/stall adjustment) |

**Pipeline-coverage ratio:** 2.72x (commit-relative)
**Pipeline-risk variance:** 42.2% (commit-to-pipe gap)

## Assumption block (NON-OPTIONAL — present this on the board slide)

- **Conversion-window weighting:** 70% last-4Q + 30% last-12Q (blended)
- **Industry profile:** `saas`
- **Commit-grade stages:** closed_won_pending, commit, contract-out, contract_out, verbal
- **Best-case stages:** closed_won_pending, commit, contract-out, contract_out, demo-completed, demo_completed, negotiation, proposal, verbal
- **Time-to-close model:** linear decay; 1.0 inside window, 0.7 within 30 days late, 0.5 within 60, 0.3 within 90, 0.15 thereafter
- **Stall rule:** opp age > 2.0x median stage age AND last_activity > 45 days → contribution * 0.5

### Stage conversions applied

| Stage | Rate | Window | Rationale |
|---|---:|---|---|
| commit | 90.90% | blended | Blended 70% last-4Q (90.00%) + 30% last-12Q (93.00%). |
| contract_out | 20.00% | fallback | No historical data, no profile prior; using conservative 20% fallback. |
| demo_completed | 47.60% | blended | Blended 70% last-4Q (44.00%) + 30% last-12Q (56.00%). |
| discovery | 26.20% | blended | Blended 70% last-4Q (22.00%) + 30% last-12Q (36.00%). |
| negotiation | 71.80% | blended | Blended 70% last-4Q (70.00%) + 30% last-12Q (76.00%). |
| proposal | 58.30% | blended | Blended 70% last-4Q (55.00%) + 30% last-12Q (66.00%). |
| verbal | 83.20% | blended | Blended 70% last-4Q (82.00%) + 30% last-12Q (86.00%). |

## Warnings
- ⚠️  Pipeline coverage ratio is 2.72x — below the 3.0x SaaS-industry floor. Commit is structurally unsupported (Pacific Crest / KeyBanc SaaS Survey).
- ⚠️  Best-case is 90.7% of pipe-only — likely hockey-sticking (OpenView SaaS forecasting benchmarks).

## Per-opp contributions (top 10 by commit)

| Opp | Stage | Amount | Conv | TTC | Stalled | Commit $ |
|---|---|---:|---:|---:|:---:|---:|
| OPP-305 | verbal | $420,000 | 83% | 100% | - | $349,440 |
| OPP-301 | commit | $280,000 | 91% | 100% | - | $254,520 |
| OPP-302 | commit | $195,000 | 91% | 100% | - | $177,255 |
| OPP-304 | verbal | $165,000 | 83% | 100% | - | $137,280 |
| OPP-303 | contract_out | $340,000 | 20% | 100% | - | $68,000 |
| OPP-306 | verbal | $135,000 | 83% | 50% | - | $56,160 |
| OPP-307 | negotiation | $250,000 | 72% | 100% | - | $0 |
| OPP-308 | negotiation | $180,000 | 72% | 100% | - | $0 |
| OPP-309 | proposal | $220,000 | 58% | 100% | - | $0 |
| OPP-310 | proposal | $155,000 | 58% | 70% | - | $0 |

## Next steps
1. Run `cohort_arr_projector.py` to surface leaky cohorts in NRR.
2. Run `funnel_confidence_scorer.py` to score per-stage reliability (CoV).
3. Present commit + best-case + pipe-only WITH the assumption block. No assumption block = theatre.
