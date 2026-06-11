# E-mail

## Purpose

E-mail is used for test messages, alerts, scheduled reports and executive summaries.

## Sending

SMTP or OAuth providers are used for sending:

```env
EMAIL_PROVIDER=smtp
EMAIL_DELIVERY_MODE=mock
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASS=
EMAIL_FROM=
```

Use `EMAIL_DELIVERY_MODE=live` only when credentials are real and the environment is safe for outbound messages.

## Gmail And Outlook

Gmail/Google and Outlook/Microsoft 365 usually require OAuth or app-specific credentials depending on organization policy. Document customer-specific requirements during onboarding.

## IMAP And POP3

SMTP/OAuth are mainly for sending. IMAP and POP3 are for reading/querying mailboxes and should not be presented as delivery providers.

## UI Requirements

The settings screen should show:

- provider status;
- send capability;
- read capability when IMAP/POP3 is configured;
- last test time;
- readable error;
- send test button;
- save button;
- masked secrets.

## Production Gaps

- OAuth consent app must be created for Google/Microsoft production.
- Bounce handling and delivery receipts are not final.
- Report attachments and templates need customer-specific review.
