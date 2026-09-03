# B2B SaaS Tracking Plan

## Overview
- **Product:** B2B SaaS (web app + marketing site)
- **Tools:** GA4 (analytics), Google Tag Manager (tag delivery)
- **Last updated:** 2026-08-07
- **Decisions this data informs:**
  - Which acquisition channels drive the most signups that convert to paid (channel ROI)
  - Which features correlate with upgrade/retention (product-led growth levers)
  - Where users drop off in the signup → activation → upgrade funnel
  - Upgrade path optimization (which plans users move between)

---

## Events

### 1. Signup Funnel

| Event Name | Description | Properties | Trigger |
|------------|-------------|------------|---------|
| signup_started | User initiated signup (clicked "Start free"/"Sign up") | source, page, utm_source, utm_medium, utm_campaign | CTA click on marketing site or in-app upsell |
| signup_step_completed | User completed a signup form step | step_number, step_name (email, password, company, verify) | Each step of multi-step signup |
| signup_completed | Account successfully created | method (email/google/sso), plan (free/trial), account_id | Post-creation redirect / welcome screen |
| onboarding_started | User began product onboarding | - | First onboarding screen load |
| onboarding_step_completed | Finished an onboarding step | step_number, step_name | Step advance |
| onboarding_completed | All onboarding steps done | steps_completed, time_to_complete_s | Final step submit |

### 2. Feature Usage

| Event Name | Description | Properties | Trigger |
|------------|-------------|------------|---------|
| feature_used | Core feature interaction | feature_name, feature_category, account_id, plan_type | Feature action completes (debounce repeated rapid calls) |
| feature_viewed | User opened/loaded a feature screen | feature_name, feature_category | Feature page/modal load |
| content_created | User created a record/object in the product | content_type, account_id | Save/create success |
| search_performed | In-app search used | query, results_count, feature_name | Search submit |
| invite_sent | User invited a teammate | invite_type (email/link), count, role | Invite sent success |
| integration_connected | Third-party integration connected | integration_name | OAuth/setup success |
| integration_disconnected | Integration removed | integration_name, reason | Disconnect confirmed |

### 3. Upgrade / Monetization

| Event Name | Description | Properties | Trigger |
|------------|-------------|------------|---------|
| pricing_viewed | Pricing page seen | source (marketing/nav/in-app), account_id | Pricing page load |
| plan_selected | User chose a plan to upgrade to | plan_name, billing_cycle (monthly/annual), from_plan | Plan card click |
| checkout_started | Entered checkout flow | plan, value, currency, account_id | Checkout page load |
| payment_info_entered | Payment details submitted | payment_method (card/ach/invoice) | Payment form submit |
| subscription_upgraded | Plan upgraded successfully | from_plan, to_plan, value, currency, transaction_id, account_id | Payment success / webhook confirmed |
| purchase_completed | New paid subscription (first-time) | plan, value, currency, transaction_id, account_id | Payment success |
| subscription_downgrade_initiated | User started downgrade flow | from_plan, to_plan, reason | Downgrade CTA click |
| subscription_cancelled | Subscription cancelled | plan, reason, tenure_months, mrr_lost | Cancel confirmed |

### 4. Account / Team (B2B context)

| Event Name | Description | Properties | Trigger |
|------------|-------------|------------|---------|
| team_created | New workspace/org created | team_size, plan | Workspace creation |
| team_member_joined | Teammate accepted invite | role | Accept invite landing |
| role_changed | User permissions updated | old_role, new_role, account_id | Role save |

---

## Custom Dimensions (GA4)

Create these under **Admin → Data display → Custom definitions** so event parameters become reportable.

| Dimension Name | Scope | Event Parameter | Description |
|----------------|-------|-----------------|-------------|
| Plan Type | User | plan_type | free / starter / pro / enterprise |
| Account ID | User | account_id | Workspace/org identifier (hashed if PII risk) |
| User Type | User | user_type | free / trial / paid |
| Feature Name | Event | feature_name | Which feature was used |
| Feature Category | Event | feature_category | Grouping of features |
| Signup Method | Event | method | email / google / sso |
| From Plan | Event | from_plan | Previous plan on upgrade/downgrade |
| To Plan | Event | to_plan | New plan on upgrade/downgrade |
| Signup Source | Event | source | Channel/page that drove signup |
| Content Type | Event | content_type | Type of object created |

**Custom metrics:**

| Metric Name | Scope | Parameter | Unit |
|-------------|-------|-----------|------|
| Time to Complete | Event | time_to_complete_s | Seconds |
| MRR Lost | User | mrr_lost | Currency (numeric) |
| Value | Event | value | Currency (numeric) |

---

## Conversions (mark in GA4 Admin → Events)

| Conversion | Event | Counting Method | Notes |
|------------|-------|-----------------|-------|
| Signup | signup_completed | Once per session | Primary acquisition conversion |
| Onboarding Complete | onboarding_completed | Once per session | Activation milestone |
| Upgrade | subscription_upgraded | Every event | Revenue event; set value |
| Purchase | purchase_completed | Every event | First-time paid; include value & currency |
| Integration Connected | integration_connected | Once per session | "Aha"/stickiness signal |

---

## Implementation

### GTM Container Setup

**Naming convention** (per Skill: `[Type] - [Description] - [Detail]`):

| Component | Name | Purpose |
|-----------|------|---------|
| Tag | GA4 - Config - Base | GA4 base config, fires on All Pages |
| Tag | GA4 - Event - Signup Completed | Fires on `signup_completed` custom event |
| Tag | GA4 - Event - Feature Used | Fires on `feature_used` custom event |
| Tag | GA4 - Event - Subscription Upgraded | Fires on `subscription_upgraded` custom event |
| Tag | GA4 - Event - Purchase | Fires on `purchase` custom event |
| Trigger | Custom - signup_completed | Data layer event = `signup_completed` |
| Trigger | Custom - feature_used | Data layer event = `feature_used` |
| Trigger | Custom - subscription_upgraded | Data layer event = `subscription_upgraded` |
| Trigger | Custom - purchase | Data layer event = `purchase` |
| Variable | DL - plan_type | Data layer variable `plan_type` |
| Variable | DL - feature_name | Data layer variable `feature_name` |
| Variable | DL - from_plan / DL - to_plan | Upgrade path |
| Variable | DL - value / DL - currency | Revenue values |

### Data Layer Pushes (app-side code)

Initialize before GTM container in `<head>`:
```javascript
window.dataLayer = window.dataLayer || [];
```

**Signup completed:**
```javascript
dataLayer.push({
  'event': 'signup_completed',
  'method': 'email',
  'plan': 'free',
  'account_id': 'acct_12345'
});
```

**Feature used (fire on meaningful completion, not every click):**
```javascript
dataLayer.push({
  'event': 'feature_used',
  'feature_name': 'report_builder',
  'feature_category': 'analytics',
  'account_id': 'acct_12345',
  'plan_type': 'pro'
});
```

**Upgrade:**
```javascript
dataLayer.push({ ecommerce: null }); // clear previous
dataLayer.push({
  'event': 'subscription_upgraded',
  'from_plan': 'starter',
  'to_plan': 'pro',
  'value': 49.00,
  'currency': 'USD',
  'transaction_id': 'sub_67890',
  'account_id': 'acct_12345'
});
```

**Set user properties on login/plan change:**
```javascript
dataLayer.push({
  'user_id': 'usr_abc',       // GA4 user_id (non-PII)
  'user_type': 'paid',
  'plan_type': 'pro',
  'account_id': 'acct_12345'
});
```

### GA4 Config Tag Settings
- Measurement ID: `G-XXXXXXXX`
- Send page view: enabled
- **User properties** mapped: `plan_type`, `user_type`, `account_id`
- Enable **enhanced measurement** (page_view, scroll, outbound_click, file_download, site_search)
- Set **data retention** to 14 months
- Define **internal traffic** filter to exclude dev/employee IPs
- Configure **cross-domain tracking** if marketing site and app are on different domains

### Consent / Privacy (GDPR/CCPA)
```javascript
// Default deny before consent banner
gtag('consent', 'default', {
  'analytics_storage': 'denied',
  'ad_storage': 'denied'
});
// On consent granted:
gtag('consent', 'update', {
  'analytics_storage': 'granted',
  'ad_storage': 'granted'
});
```
- Enable GTM **Consent Overview**; gate GA4 tags behind consent
- **No PII** in event parameters (hash emails; never send raw emails/phone in properties)
- IP anonymization on by default in GA4

---

## UTM Convention (marketing links)

| Parameter | Convention | Example |
|-----------|------------|---------|
| utm_source | platform name, lowercase | google, linkedin, producthunt |
| utm_medium | channel type | cpc, email, social, organic_social |
| utm_campaign | campaign name, snake_case | q3_plg_launch_2026 |
| utm_content | creative/placement variant | hero_cta, sidebar_banner |
| utm_term | paid keyword (paid search only) | b2b_analytics_tool |

Persist first-touch UTMs to `signup_completed.source` / campaign properties so signup-to-paid attribution works.

---

## Validation Checklist (before publish)

- [ ] GTM Preview Mode: each custom event tag fires on correct data layer push
- [ ] GA4 DebugView shows events with all expected parameters populated
- [ ] No duplicate events (check for double-firing in SPA route changes)
- [ ] `value` and `currency` present on `subscription_upgraded` / `purchase_completed`
- [ ] Custom dimensions created in GA4 and parameter names match exactly
- [ ] Conversions marked and counting method correct (signups = once/session, purchases = every)
- [ ] Internal traffic excluded; test events not in production view
- [ ] No PII (emails, names, phone) in any event parameter
- [ ] Consent mode: tags do not fire before consent in EU/UK/CA sessions
- [ ] Cross-domain linker working between marketing site and app
- [ ] Tested on Chrome, Safari, Firefox, and mobile web

---

## Funnels to Build in GA4 Explorations

1. **Acquisition → Activation:** `signup_started` → `signup_completed` → `onboarding_completed` → `first feature_used`
2. **Upgrade path:** `pricing_viewed` → `plan_selected` → `checkout_started` → `payment_info_entered` → `subscription_upgraded`
3. **Feature adoption by plan:** segment `feature_used` by `plan_type` to see what paid users use that free users don't
4. **Integration stickiness:** compare retention/conversion for users with `integration_connected` vs. without
