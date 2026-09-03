#!/usr/bin/env python3
"""
Run org-health-diagnostic scorer on BEFORE and AFTER reorg scenarios.
Imports the Skill's health_scorer.py to use its exact scoring logic.
"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "org-health-diagnostic", "scripts"))
from health_scorer import (
    Stage, Trend, build_financial_dimension, build_revenue_dimension,
    build_product_dimension, build_engineering_dimension, build_people_dimension,
    build_operations_dimension, build_security_dimension, build_market_dimension,
    calculate_overall, to_json
)

STAGE = Stage.SERIES_B  # reorg typical at Series B when functions formalize

# ============================================================
# BEFORE reorg — "tribe of 40", generalists, high trust but fuzzy roles
# Mapped from simulated interview summary (pre-reorg).
# ============================================================
before = dict(
    # Financial — unchanged by reorg in short term
    runway=14, burn_multiple=1.8, gross_margin=68, mom_growth=7.0,
    revenue_concentration=18, financial_trend=Trend.STABLE,
    # Revenue — unchanged
    nrr=112, logo_churn=7, pipeline_coverage=2.8, cac_payback=14,
    win_rate=24, revenue_trend=Trend.STABLE,
    # Product — unchanged
    nps=44, dau_mau=38, feature_adoption=58, csat=4.2,
    ttv_days=4, product_trend=Trend.STABLE,
    # Engineering — pace: weekly deploys, rising tech debt, MTTR ok
    deploy_freq=3,             # weekly
    change_failure_rate=12,
    mttr_hours=2.5,
    tech_debt_pct=28,
    incidents_monthly=2,
    engineering_trend=Trend.DECLINING,
    # People — TRUST: high eNPS, low attrition, but fuzzy spans, slow hiring
    attrition=9,               # <10% green for Series B
    enps=42,                   # high
    ttf_days=75,               # yellow — hiring slow because no clear roles
    internal_promo_rate=22,    # yellow
    people_trend=Trend.STABLE,
    # Operations — ROLE CLARITY / DECISION PACE: fuzzy, slow decisions, low process
    okr_completion=58,
    decision_hours=120,        # 5 days — yellow/red
    process_maturity=2.0,      # yellow
    xfn_delivery_rate=55,      # red — handoffs unclear
    ops_trend=Trend.DECLINING,
    # Security — unchanged
    incidents_90d=0, mfa_coverage=92, training_completion=88,
    cve_patch_rate=96, pentest_months=10, security_trend=Trend.STABLE,
    # Market — unchanged
    organic_pipeline_pct=42, competitive_win_rate=48,
    cac_trend_score=3, market_trend=Trend.STABLE,
)

# ============================================================
# AFTER reorg — functional leads added, RACI introduced, pods formed
# Mapped from simulated interview summary (post-reorg, ~90 days in).
# ============================================================
after = dict(
    runway=14, burn_multiple=1.8, gross_margin=68, mom_growth=7.0,
    revenue_concentration=18, financial_trend=Trend.STABLE,
    nrr=112, logo_churn=7, pipeline_coverage=2.8, cac_payback=14,
    win_rate=24, revenue_trend=Trend.STABLE,
    nps=44, dau_mau=38, feature_adoption=58, csat=4.2,
    ttv_days=4, product_trend=Trend.STABLE,
    # Engineering — pace: short-term dip (new process overhead), debt being addressed
    deploy_freq=2,             # monthly — dipped during transition
    change_failure_rate=8,     # improved — reviews added
    mttr_hours=1.5,            # improved — on-call rotation formalized
    tech_debt_pct=22,          # improving — debt sprints scheduled
    incidents_monthly=1,
    engineering_trend=Trend.STABLE,  # short-term dip but signs of recovery
    # People — TRUST: eNPS dropped, attrition up, spans clearer
    attrition=14,              # yellow — 2 regrettable exits post-reorg
    enps=18,                   # dropped sharply — "feels corporate", uncertainty
    ttf_days=40,               # improved — clear role specs
    internal_promo_rate=30,    # improved — new leads promoted internally
    people_trend=Trend.DECLINING,
    # Operations — ROLE CLARITY / PACE: much clearer, faster decisions, better xfn
    okr_completion=72,         # green
    decision_hours=36,         # <48h green
    process_maturity=3.0,      # green
    xfn_delivery_rate=74,      # green
    ops_trend=Trend.IMPROVING,
    incidents_90d=0, mfa_coverage=94, training_completion=92,
    cve_patch_rate=97, pentest_months=10, security_trend=Trend.IMPROVING,
    organic_pipeline_pct=42, competitive_win_rate=48,
    cac_trend_score=3, market_trend=Trend.STABLE,
)

def build_all(data, stage):
    return [
        build_financial_dimension(stage, **data),
        build_revenue_dimension(stage, **data),
        build_product_dimension(**data),
        build_engineering_dimension(**data),
        build_people_dimension(stage, **data),
        build_operations_dimension(**data),
        build_security_dimension(**data),
        build_market_dimension(**data),
    ]

dims_before = build_all(before, STAGE)
dims_after  = build_all(after, STAGE)

overall_before = calculate_overall(dims_before, STAGE)
overall_after  = calculate_overall(dims_after, STAGE)

print("=" * 70)
print(f"STAGE: {STAGE.value}")
print(f"OVERALL BEFORE: {overall_before}  |  AFTER: {overall_after}  |  DELTA: {round(after_overall := overall_after - overall_before, 1) if (overall_before and overall_after) else 'n/a'}")
print("=" * 70)

focus = {"engineering", "people", "operations"}

for label, dims in [("BEFORE", dims_before), ("AFTER", dims_after)]:
    print(f"\n--- {label} ---")
    for d in dims:
        s = d.score()
        tl = d.traffic_light().value
        tr = d.trend.value
        if d.key in focus:
            print(f"  * {d.emoji} {d.name:<22} {tl.upper():<6} {s}  trend={tr}")
            for m in d.metrics:
                ms = m.score()
                mtl = m.traffic_light().value if m.traffic_light() else "n/a"
                print(f"      - {m.name:<32} val={m.value}  score={ms}  {mtl}")
        else:
            print(f"    {d.emoji} {d.name:<22} {tl.upper():<6} {s}  trend={tr}")

# JSON dump for record
out = {
    "stage": STAGE.value,
    "before": to_json(dims_before, overall_before, STAGE),
    "after":  to_json(dims_after, overall_after, STAGE),
}
with open(os.path.join(os.path.dirname(__file__), "before_after_scores.json"), "w") as f:
    json.dump(out, f, indent=2)
print("\nWrote before_after_scores.json")
