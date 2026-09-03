# Funnel Confidence Scorer

**Stages scored:** 5

## Confidence band summary

| Stage | n quarters | Mean % | StDev % | CoV % | Band | Treatment |
|---|---:|---:|---:|---:|:---:|---|
| discovery_to_demo | 12 | 33.75 | 4.93 | 14.6 | **MEDIUM** | blended-weighting |
| demo_to_proposal | 12 | 52.75 | 4.46 | 8.4 | **HIGH** | commit-grade |
| proposal_to_negotiation | 12 | 62.00 | 5.83 | 9.4 | **HIGH** | commit-grade |
| negotiation_to_verbal | 12 | 74.67 | 1.18 | 1.6 | **HIGH** | commit-grade |
| verbal_to_commit | 12 | 84.75 | 1.69 | 2.0 | **HIGH** | commit-grade |

## Per-stage rationale

### discovery_to_demo — MEDIUM (blended-weighting)
- Mean 33.75% across 12 quarters; stdev 4.93%; CoV 14.6%.
- CoV 10-25% — usable but flagged. Apply blended last-4Q / last-12Q weighting.

### demo_to_proposal — HIGH (commit-grade)
- Mean 52.75% across 12 quarters; stdev 4.46%; CoV 8.4%.
- CoV < 10% — historically stable. Use as commit-grade conversion input.

### proposal_to_negotiation — HIGH (commit-grade)
- Mean 62.00% across 12 quarters; stdev 5.83%; CoV 9.4%.
- CoV < 10% — historically stable. Use as commit-grade conversion input.

### negotiation_to_verbal — HIGH (commit-grade)
- Mean 74.67% across 12 quarters; stdev 1.18%; CoV 1.6%.
- CoV < 10% — historically stable. Use as commit-grade conversion input.

### verbal_to_commit — HIGH (commit-grade)
- Mean 84.75% across 12 quarters; stdev 1.69%; CoV 2.0%.
- CoV < 10% — historically stable. Use as commit-grade conversion input.

## Confidence-band thresholds (assumption block)

- **HIGH** — CoV < 10%. Commit-grade conversion input.
- **MEDIUM** — CoV 10-25%. Use blended last-4Q / last-12Q weighting.
- **LOW** — CoV 25-50%. Soft floor only; never a commit input.
- **VERY LOW** — CoV > 50%. Statistical noise; root-cause before using.
- **Min sample size** — 4 quarters for stable CoV; below that → extend-data-window.

## Next steps
1. For any stage flagged `do-not-use` or `treat-as-soft-floor`, decompose: segment? motion? rep? quarter-of-year seasonality?
2. Feed HIGH and MEDIUM stages directly into `bookings_forecaster.py`. Exclude LOW and VERY LOW from commit.
3. Present the per-stage confidence table on the same slide as the 3-tier forecast number.
