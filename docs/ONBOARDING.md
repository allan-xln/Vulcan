# Onboarding

## Goal

A new customer must understand the path from contract to first insight without needing a developer beside them.

## Customer Activation Flow

1. Create company tenant.
2. Create tenant admin.
3. Create departments.
4. Create users.
5. Build hierarchy.
6. Generate enrollment token.
7. Install Linux/Windows agent.
8. Confirm device online.
9. Configure WhatsApp recipients.
10. Configure e-mail provider.
11. Configure AI provider or accept explicit mock mode.
12. Configure report schedules.
13. Review dashboard and first recommendations.

## Dashboard Checklist

The dashboard exposes a paid-pilot checklist with:

- company/database configured;
- users and hierarchy;
- agents connected;
- operational/executive AI;
- WhatsApp alerts;
- e-mail reports;
- scheduled reports.

## Minimum Paid Pilot Setup

```text
Tenant: customer company
Admin: company owner or operations manager
Users: director, coordinator, manager, supervisor, team lead, operators
Agents: at least 3 real devices
Channels: WhatsApp root channel plus one e-mail sender
Reports: daily operational report and weekly executive report
```

## Data Quality Rules

- First day: use agent health and connectivity as the main success indicator.
- Days 2-3: validate idle, active time, context switches and top apps.
- Week 1: review bottlenecks and false positives.
- Week 2+: use trends, automation opportunities and executive recommendations.

## What Is Still Manual

- Customer self-service signup is not complete.
- Payment/subscription flow is not implemented.
- Windows package must be tested on a real Windows machine for production rollout.
- macOS is documented as skeleton/placeholder until native collector is built.
