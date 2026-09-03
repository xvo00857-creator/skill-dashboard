# Cohort ARR Projection

**Horizon:** 4 quarters  •  **Cohorts:** 7  •  **Leaky cohorts:** 2

## Leaky-cohort callout

> The consolidated NRR can stay flat while a recent cohort is leaking. Surfacing the leak now is 2-3 quarters cheaper than discovering it in the topline. (Campbell / Skok cohort decomposition.)

- ⚠️  **2026-Q1** (2026-Q1): Mean NRR 94.2% is 6.0 pp below trailing-cohort avg 100.2% (threshold: 5.0 pp).
- ⚠️  **2026-Q2** (2026-Q2): Mean NRR 83.8% is 15.5 pp below trailing-cohort avg 99.2% (threshold: 5.0 pp).

## Per-cohort NRR heatmap (% by projection quarter)

| Cohort | Acq Q | Starting ARR | Q+1 | Q+2 | Q+3 | Q+4 |
|---|---|---:|---:|---:|---:|---:|
| 2024-Q4 | 2024-Q4 | $800,000 | 100.0% | 102.0% | 103.0% | 104.0% |
| 2025-Q1 | 2025-Q1 | $900,000 | 98.0% | 100.0% | 101.0% | 102.0% |
| 2025-Q2 | 2025-Q2 | $1,000,000 | 100.0% | 101.0% | 102.0% | 103.0% |
| 2025-Q3 | 2025-Q3 | $1,100,000 | 98.0% | 99.0% | 100.0% | 101.0% |
| 2025-Q4 | 2025-Q4 | $1,200,000 | 97.0% | 97.0% | 98.0% | 99.0% |
| 2026-Q1 ⚠️ | 2026-Q1 | $1,040,000 | 94.0% | 94.0% | 94.0% | 95.0% |
| 2026-Q2 ⚠️ | 2026-Q2 | $910,000 | 86.0% | 84.0% | 83.0% | 82.0% |

## Consolidated NRR / GRR trajectory

| Quarter | Consolidated NRR | Consolidated GRR | Consolidated ARR |
|---|---:|---:|---:|
| Q+1 | 96.2% | 91.5% | $6,684,200 |
| Q+2 | 96.7% | 89.6% | $6,721,000 |
| Q+3 | 97.3% | 88.4% | $6,761,900 |
| Q+4 | 98.0% | 87.3% | $6,813,200 |

## Assumption block (NON-OPTIONAL — present alongside the cohort heatmap)

- **projection_horizon_quarters:** 4
- **leak_threshold_pp:** 5.0
- **leak_rule:** Cohort flagged leaky if mean NRR is ≥ 5.0 pp below the mean of all earlier-acquired cohorts (Campbell/ProfitWell cohort decomposition discipline).
- **consolidation_method:** ARR-weighted (starting_arr) across cohorts per quarter
- **default_grr_curve_when_missing:** 92% Q1 decaying ~1pp/quarter, floor 85%
- **default_expansion_curve_when_missing:** 4% Q1 ramping +2pp/quarter, ceiling 12%

## Next steps
1. If a leaky cohort is flagged, decompose it: which segment / motion / pricing tier dominates that cohort?
2. Cross-check against the bookings forecast — leaky cohort + flat commit number is a hidden mismatch.
3. Present NRR with the cohort heatmap. Consolidated-only is theatre.
