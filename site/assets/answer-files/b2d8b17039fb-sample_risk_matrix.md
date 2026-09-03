# Vendor Risk Matrix — `saas` profile

**Summary:** 4 Critical · 0 High · 0 Medium · 1 Low

## Risk Matrix

| Vendor | Category | Data | Financial | Operational | Regulatory | Overall |
|---|---|---|---|---|---|---|
| Okta | identity | High | High | High | Medium | **Critical** |
| Snowflake | data-warehouse | Critical | Critical | Critical | Medium | **Critical** |
| LegacyCRM | crm | High | Medium | High | Medium | **Critical** |
| BoutiqueQA | qa-services | High | Medium | Low | High | **Critical** |
| ChartingTool | analytics | Low | Low | Low | Low | **Low** |

## Mitigations

### Okta — Critical
- Confirm data-processing addendum (DPA) is current. Require encryption at rest + in transit.
- Require liability cap parity (≥ 12 months of fees). Confirm insurance certificate on file.

### Snowflake — Critical
- Confirm data-processing addendum (DPA) is current. Require encryption at rest + in transit.
- Require liability cap parity (≥ 12 months of fees). Confirm insurance certificate on file.
- Document a 72-hour break-glass plan. Identify and pre-qualify a backup vendor.

### LegacyCRM — Critical
- Confirm data-processing addendum (DPA) is current. Require encryption at rest + in transit.

### BoutiqueQA — Critical
- Confirm data-processing addendum (DPA) is current. Require encryption at rest + in transit.
- Request most recent SOC2 Type II report; review exceptions section.

### ChartingTool — Low
- No critical mitigations required; routine annual review.
