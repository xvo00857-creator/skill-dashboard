# Sample Specification

## Table of Contents

- Goals
- Architecture
- Risks

## Goals

We will integrate **Stripe Connect** with the existing checkout flow.

| Phase | Timeline | Owner |
|-------|----------|-------|
| Design | Week 1 | jane |
| Build | Week 2-3 | dev team |
| Ship | Week 4 | jane |

## Architecture

The integration uses webhooks for async events.

```python
def handle_webhook(event):
    if event.type == "payment.succeeded":
        mark_paid(event.data.object.id)
```

> [!NOTE]
> All webhook handlers must be idempotent.

> [!WARNING]
> Tax calculation has edge cases for digital goods in the EU.

## Risks

1. Webhook delivery delays
2. Tax calculation edge cases for VAT
3. Refund cascading across multi-party transfers

See [Stripe Connect docs](https://stripe.com/docs/connect) for details.
