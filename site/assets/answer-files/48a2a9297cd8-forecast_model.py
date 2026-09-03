#!/usr/bin/env python3
"""
Monthly revenue forecast for a ¥99/mo team tool.

Adapts the commercial-forecaster Skill discipline (3-tier commit/best-case/pipe-only,
non-optional assumption block, cohort NRR/GRR decomposition, CoV funnel-confidence
scoring, pipeline-coverage check) to a monthly PLG / SMB-SaaS model.

No real customer data was provided; all operating numbers are PLANNING ASSUMPTIONS
calibrated to public SaaS benchmarks cited in the Skill's reference canon
(OpenView, KeyBanc/Pacific Crest, David Skok, Tomasz Tunguz, ProfitWell/Campbell,
BVP, Winning by Design). Replace with actuals before using for a board commit.
"""
from __future__ import annotations

import json
import math
import statistics
from dataclasses import dataclass, field
from typing import Callable

# ---------------------------------------------------------------------------
# 1. ASSUMPTIONS  (all explicit; all replaceable)
# ---------------------------------------------------------------------------

PRICE_BASE = 99.0          # ¥ / workspace / month, base plan
HORIZON_MONTHS = 12
MONTH_LABELS = [
    "2026-09","2026-10","2026-11","2026-12",
    "2027-01","2027-02","2027-03","2027-04",
    "2027-05","2027-06","2027-07","2027-08",
]
M0_LABEL = "2026-08"

# Starting book of business (M0 = 2026-08)
START_PAID_TEAMS = 300     # planning assumption
START_ARPU = 99.0

# --- Three tiers, mapping the Skill's commit / best-case / pipe-only ---------
# commit  = conservative, defensible even if execution slips
# best-case = planning baseline (the number you run the business on)
# pipe-only = optimistic ceiling if every top-of-funnel and retention
#             assumption breaks your way (no stall / friction penalty)
#
# Conversion-window note: the Skill blends 70% last-4Q + 30% last-12Q.
# Without company history we use a single industry-prior point estimate per
# tier and flag that the blend MUST be recomputed once 4+ quarters of real
# conversion history exist.

@dataclass
class Scenario:
    name: str
    trials_m1: float           # new free trials entering month 1
    trials_mom_growth: float   # month-over-month trials growth
    trial_to_paid: float       # fraction of trials that convert to paid in-month
    # monthly GRR by cohort age (index 0 = first month after signup)
    grr_curve: list[float]
    # monthly expansion rate applied to surviving MRR (upgrades + add-ons)
    expansion_mom: float
    # pipeline-coverage analogue: top-of-funnel "coverage" of new paid logos
    # = trials in month / (trials needed to hit the planned new-paid number at t2p)
    # We surface this; the Skill's 3x rule maps to ~3x trials coverage in PLG.

SCENARIOS: dict[str, Scenario] = {
    "commit": Scenario(
        name="commit (conservative)",
        trials_m1=1000,
        trials_mom_growth=0.05,
        trial_to_paid=0.035,
        # SMB SaaS: first-month churn elevated, then settles
        grr_curve=[0.93, 0.96, 0.965, 0.965] + [0.96]*8,   # ~4% mature mo. churn
        expansion_mom=0.008,
    ),
    "best_case": Scenario(
        name="best-case (baseline)",
        trials_m1=1200,
        trials_mom_growth=0.07,
        trial_to_paid=0.050,
        grr_curve=[0.95, 0.97, 0.97, 0.97] + [0.97]*8,     # ~3% mature mo. churn
        expansion_mom=0.015,
    ),
    "pipe_only": Scenario(
        name="pipe-only (optimistic ceiling)",
        trials_m1=1500,
        trials_mom_growth=0.10,
        trial_to_paid=0.070,
        grr_curve=[0.97, 0.98, 0.98, 0.98] + [0.98]*8,     # ~2% mature mo. churn
        expansion_mom=0.025,
    ),
}

# Funnel stages (visitor -> paid) with industry-prior conversion means.
# Sources: OpenView SaaS benchmarks, KeyBanc/Pacific Crest Private SaaS Survey,
# David Skok (For Entrepreneurs), ProfitWell/Paddle PLG benchmarks.
# NOTE: no 12-quarter company history was provided, so per the Skill's
# funnel_confidence_scorer.py (n<4 -> "extend-data-window"), every stage is
# flagged for calibration once real data exists.
FUNNEL_STAGES = [
    {"stage": "visitor -> signup",        "prior_mean": 0.08, "source": "OpenView / Landing-page benchmark 5-12%"},
    {"stage": "signup -> activated",      "prior_mean": 0.35, "source": "Reforge / Balfour PLG activation 30-50%"},
    {"stage": "activated -> trial start", "prior_mean": 0.20, "source": "Winning by Design bowtie model"},
    {"stage": "trial -> paid",            "prior_mean": 0.05, "source": "ProfitWell PLG median 2-8%; best-case 5%"},
]

# ---------------------------------------------------------------------------
# 2. CORE MODEL
# ---------------------------------------------------------------------------

def grr_for_age(scn: Scenario, age_months: int) -> float:
    """GRR applied to a cohort when it is `age_months` old (0 = month of signup)."""
    if age_months < len(scn.grr_curve):
        return scn.grr_curve[age_months]
    return scn.grr_curve[-1]

def project(scn: Scenario) -> dict:
    """
    Project 12 months. Returns a dict with monthly cohorts, MRR, paid teams,
    ARPU, new/churned/expansion MRR, and cohort-level NRR/GRR.

    Cohort convention:
      - A cohort "born" at projection month m carries `start_teams` teams at
        the end of month m (no in-month churn).
      - For every subsequent month m' > m, we apply grr_curve[age-1] where
        age = m' - m, then apply expansion on the surviving MRR.
      - The M0 (legacy) book is a cohort born at month -1 with start_teams =
        START_PAID_TEAMS; it is already mature, so every projection month
        applies the mature (last) GRR value.
    """
    months = MONTH_LABELS

    # cohorts: list of dicts, each with start_month, start_teams, start_arpu,
    # and parallel lists teams_by_month / mrr_by_month of length HORIZON_MONTHS.
    cohorts: list[dict] = []

    # Seed M0 book as a single mature "legacy" cohort.
    cohorts.append({
        "cohort_id": f"legacy-{M0_LABEL}",
        "start_month": -1,
        "start_teams": float(START_PAID_TEAMS),
        "start_arpu": START_ARPU,
        "teams_by_month": [],   # filled for m=0..11
        "mrr_by_month": [],
    })

    monthly_new_paid = []
    monthly_trials = []
    monthly_churned_teams = []
    monthly_churned_mrr = []
    monthly_expansion_mrr = []
    monthly_total_paid = []
    monthly_total_mrr = []
    monthly_new_mrr = []

    for m in range(HORIZON_MONTHS):
        trials = scn.trials_m1 * ((1 + scn.trials_mom_growth) ** m)
        new_paid = trials * scn.trial_to_paid
        new_mrr = new_paid * PRICE_BASE
        monthly_trials.append(trials)
        monthly_new_paid.append(new_paid)
        monthly_new_mrr.append(new_mrr)

        # Add new cohort for this month's signups (end-of-month, no churn yet)
        cohorts.append({
            "cohort_id": f"C{months[m]}",
            "start_month": m,
            "start_teams": new_paid,
            "start_arpu": PRICE_BASE,
            "teams_by_month": [],
            "mrr_by_month": [],
        })

        total_paid = 0.0
        total_mrr = 0.0
        churned_teams = 0.0
        churned_mrr = 0.0
        expansion_mrr = 0.0

        for c in cohorts:
            age = m - c["start_month"]   # 0 = signup month, >0 = subsequent
            if age == 0:
                # Signup month: book the new teams at start ARPU, no churn
                teams_now = c["start_teams"]
                mrr_now = teams_now * c["start_arpu"]
            else:
                # Age forward from previous month (or from start if first month)
                if c["teams_by_month"]:
                    prev_teams = c["teams_by_month"][-1]
                    prev_mrr = c["mrr_by_month"][-1]
                else:
                    prev_teams = c["start_teams"]
                    prev_mrr = c["start_teams"] * c["start_arpu"]
                arpu_prev = prev_mrr / prev_teams if prev_teams > 0 else c["start_arpu"]
                # Which GRR bucket?
                if c["start_month"] == -1:
                    # Legacy cohort: always mature
                    grr = scn.grr_curve[-1]
                else:
                    # age-1 indexes into grr_curve for the transition from (age-1) to age
                    grr = grr_for_age(scn, age - 1)
                teams_after_churn = prev_teams * grr
                churned_teams += prev_teams - teams_after_churn
                churned_mrr += (prev_teams - teams_after_churn) * arpu_prev
                mrr_after_churn = teams_after_churn * arpu_prev
                exp = mrr_after_churn * scn.expansion_mom
                mrr_now = mrr_after_churn + exp
                teams_now = teams_after_churn
                expansion_mrr += exp

            c["teams_by_month"].append(teams_now)
            c["mrr_by_month"].append(mrr_now)
            total_paid += teams_now
            total_mrr += mrr_now

        monthly_total_paid.append(total_paid)
        monthly_total_mrr.append(total_mrr)
        monthly_churned_teams.append(churned_teams)
        monthly_churned_mrr.append(churned_mrr)
        monthly_expansion_mrr.append(expansion_mrr)

    # Cohort NRR / GRR at month-12 horizon (relative to each cohort's start)
    cohort_metrics = []
    for c in cohorts:
        start_mrr = c["start_teams"] * c["start_arpu"]
        if start_mrr <= 0:
            continue
        end_idx = len(c["mrr_by_month"]) - 1
        end_mrr = c["mrr_by_month"][end_idx]
        end_teams = c["teams_by_month"][end_idx]
        grr_end = end_teams / c["start_teams"]
        nrr_end = end_mrr / start_mrr
        cohort_metrics.append({
            "cohort_id": c["cohort_id"],
            "start_month": c["start_month"],
            "start_teams": c["start_teams"],
            "start_mrr": start_mrr,
            "end_teams": end_teams,
            "end_mrr": end_mrr,
            "grr_to_date": grr_end,
            "nrr_to_date": nrr_end,
        })

    # Consolidated NRR/GRR: compare M12 MRR to (M0 MRR + sum of new MRR added)
    # This is the "net of everything" retention on the starting book + new logos.
    m0_mrr = START_PAID_TEAMS * START_ARPU
    total_new_mrr = sum(monthly_new_mrr)
    m12_mrr = monthly_total_mrr[-1]
    # Quick ratio: (new + expansion) / churn
    quick_ratio = (sum(monthly_new_mrr) + sum(monthly_expansion_mrr)) / max(sum(monthly_churned_mrr), 1)

    # Pipeline-coverage analogue: trials coverage = total trials over 12mo /
    # trials needed to produce the committed new-paid logos at the scenario's t2p.
    # In PLG this is the top-of-funnel cushion.
    total_trials = sum(monthly_trials)
    total_new_paid = sum(monthly_new_paid)
    implied_t2p = total_new_paid / total_trials if total_trials else 0
    # 3x coverage analogue: if trials needed = new_paid / t2p_prior, coverage = trials / needed
    trials_needed = total_new_paid / scn.trial_to_paid if scn.trial_to_paid else 1
    trials_coverage = total_trials / trials_needed if trials_needed else 0  # will be 1.0 by construction

    return {
        "scenario": scn.name,
        "months": months,
        "trials": monthly_trials,
        "new_paid": monthly_new_paid,
        "new_mrr": monthly_new_mrr,
        "churned_teams": monthly_churned_teams,
        "churned_mrr": monthly_churned_mrr,
        "expansion_mrr": monthly_expansion_mrr,
        "total_paid": monthly_total_paid,
        "total_mrr": monthly_total_mrr,
        "blended_arpu": [monthly_total_mrr[i]/monthly_total_paid[i] if monthly_total_paid[i] else 0 for i in range(HORIZON_MONTHS)],
        "m0_mrr": m0_mrr,
        "m12_mrr": m12_mrr,
        "mrr_growth_12m": m12_mrr / m0_mrr - 1,
        "total_new_mrr_12m": total_new_mrr,
        "total_churned_mrr_12m": sum(monthly_churned_mrr),
        "total_expansion_mrr_12m": sum(monthly_expansion_mrr),
        "total_revenue_12m": sum(monthly_total_mrr),
        "quick_ratio": quick_ratio,
        "cohort_metrics": cohort_metrics,
        "annualized_nrr_proxy": m12_mrr / (m0_mrr + total_new_mrr) if (m0_mrr + total_new_mrr) else 0,
    }

# ---------------------------------------------------------------------------
# 3. FUNNEL CONFIDENCE (CoV) — adapted from funnel_confidence_scorer.py
# ---------------------------------------------------------------------------

def funnel_confidence() -> list[dict]:
    """
    Without company history we cannot compute empirical CoV. Per the Skill's
    hard rule (n<4 -> extend-data-window), every stage is flagged for
    calibration. We still surface the industry-prior mean and the treatment
    recommendation so the model is auditable.
    """
    rows = []
    for s in FUNNEL_STAGES:
        rows.append({
            "stage": s["stage"],
            "prior_mean": s["prior_mean"],
            "n_quarters_company_data": 0,
            "cov_band": "NOT YET MEASURABLE",
            "treatment": "extend-data-window",
            "rationale": (
                f"Industry prior {s['prior_mean']:.1%} ({s['source']}). "
                "No company conversion history provided; per the Skill's "
                "funnel_confidence_scorer (min n=4 quarters for stable CoV), "
                "this stage cannot be used as a commit-grade input until 4+ "
                "quarters of real conversion data are loaded."
            ),
        })
    return rows

# ---------------------------------------------------------------------------
# 4. SENSITIVITY ANALYSIS
# ---------------------------------------------------------------------------

def sensitivity(base: Scenario) -> list[dict]:
    """One-at-a-time sensitivity on M12 MRR and 12-mo cumulative revenue."""
    base_res = project(base)
    base_m12 = base_res["m12_mrr"]
    base_cum = base_res["total_revenue_12m"]

    rows = []
    def run(label: str, **kwargs):
        scn = Scenario(**{**base.__dict__, **kwargs})
        r = project(scn)
        rows.append({
            "variable": label,
            "m12_mrr": r["m12_mrr"],
            "m12_vs_base": r["m12_mrr"]/base_m12 - 1,
            "cum_rev_12m": r["total_revenue_12m"],
            "cum_vs_base": r["total_revenue_12m"]/base_cum - 1,
        })

    run("Base (best-case)", )
    run("Trial→Paid 3.5% (–1.5pp)", trial_to_paid=0.035)
    run("Trial→Paid 6.5% (+1.5pp)", trial_to_paid=0.065)
    run("Mature churn 4% (+1pp)",  grr_curve=[0.94,0.96,0.96,0.96]+[0.96]*8)
    run("Mature churn 2% (–1pp)",  grr_curve=[0.96,0.98,0.98,0.98]+[0.98]*8)
    run("Trials growth 4% (–3pp)", trials_mom_growth=0.04)
    run("Trials growth 10% (+3pp)",trials_mom_growth=0.10)
    run("Expansion 0.5% (–1pp)",   expansion_mom=0.005)
    run("Expansion 2.5% (+1pp)",   expansion_mom=0.025)
    run("Trials M1 900 (–25%)",    trials_m1=900)
    run("Trials M1 1500 (+25%)",   trials_m1=1500)
    return rows

# ---------------------------------------------------------------------------
# 5. LEAKY COHORT CHECK (per cohort_arr_projector.py, 5pp threshold)
# ---------------------------------------------------------------------------

def leaky_cohort_check(results_by_scenario: dict) -> list[str]:
    """Flag any cohort whose NRR is >=5pp below the trailing-cohort average."""
    notes = []
    for scn_name, r in results_by_scenario.items():
        cohorts_sorted = sorted(r["cohort_metrics"], key=lambda c: c["start_month"])
        for i, c in enumerate(cohorts_sorted):
            if i == 0:
                continue
            prior = cohorts_sorted[:i]
            prior_avg = statistics.mean(p["nrr_to_date"] for p in prior)
            gap = prior_avg - c["nrr_to_date"]
            if gap >= 0.05:
                notes.append(
                    f"[{scn_name}] {c['cohort_id']}: NRR {c['nrr_to_date']:.1%} is "
                    f"{gap*100:.1f}pp below trailing-cohort avg {prior_avg:.1%} → leaky."
                )
    if not notes:
        notes.append("No cohort crosses the 5pp leak threshold under any scenario "
                     "(retention curves are uniform by scenario by construction; "
                     "real cohort dispersion will surface here once loaded).")
    return notes

# ---------------------------------------------------------------------------
# 6. MAIN
# ---------------------------------------------------------------------------

def main():
    results = {k: project(v) for k, v in SCENARIOS.items()}
    funnel = funnel_confidence()
    sens = sensitivity(SCENARIOS["best_case"])
    leaky = leaky_cohort_check(results)

    out = {
        "scenarios": {k: results[k] for k in results},
        "funnel_confidence": funnel,
        "sensitivity": sens,
        "leaky_cohort_notes": leaky,
        "assumptions": {
            "price_base_monthly": PRICE_BASE,
            "horizon_months": HORIZON_MONTHS,
            "m0_label": M0_LABEL,
            "start_paid_teams": START_PAID_TEAMS,
            "start_arpu": START_ARPU,
            "conversion_window_weighting": (
                "70% last-4Q + 30% last-12Q is the Skill's required blend. "
                "No company history was provided, so each tier uses a single "
                "industry-prior point estimate. RECOMPUTE with real data once "
                "4+ quarters of history exist."
            ),
            "pricing_note": (
                "Base plan ¥99/workspace/month. Expansion modeled as a monthly "
                "% uplift on surviving MRR (upgrades to higher tiers + add-ons). "
                "No annual prepay / discounting modeled."
            ),
            "benchmark_sources": [
                "OpenView Partners — SaaS benchmarks (t2p, NRR, GRR)",
                "KeyBanc / Pacific Crest Private SaaS Survey (pipeline coverage, stage conversion)",
                "David Skok — For Entrepreneurs (cohort retention, stalled-pipe hygiene)",
                "Tomasz Tunguz / Theory Ventures (forecast window blending, sandbag/hockey-stick)",
                "ProfitWell / Patrick Campbell / Paddle (cohort NRR decomposition, 5pp leak threshold)",
                "Bessemer Venture Partners — State of the Cloud (NRR good/better/best)",
                "Winning by Design — Bowtie model (new + retained + expansion)",
                "MIT Sloan / Hyndman & Athanasopoulos (CoV confidence bands)",
            ],
        },
    }
    with open("forecast_output.json", "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, default=str)
    print("Wrote forecast_output.json")
    # Quick console summary
    for k, r in results.items():
        print(f"  {k:10s}  M12 MRR ¥{r['m12_mrr']:>10,.0f}  "
              f"growth {r['mrr_growth_12m']*100:>5.0f}%  "
              f"12mo rev ¥{r['total_revenue_12m']:>11,.0f}  "
              f"quick {r['quick_ratio']:.2f}x")

if __name__ == "__main__":
    main()
