# WhatsApp

## Architecture

Vulcan owns its WhatsApp notification channel. It must not depend on LanChat database tables and must not modify LanChat.

The LanChat logic can inspire provider behavior, but Vulcan keeps its own configuration, logs and delivery model.

## Root Channel

```env
ROOT_WHATSAPP_ENABLED=true
ROOT_WHATSAPP_PROVIDER=lanchat
ROOT_WHATSAPP_NUMBER=5541984166423
ROOT_WHATSAPP_NAME=Vulcan Notifications
```

Do not hardcode the number outside configuration.

## Recipients

Recipients are configured per tenant and user preference:

- owner;
- director;
- coordinator;
- manager;
- supervisor;
- team lead;
- custom recipients.

## Schedules

Supported schedule model:

- immediate;
- daily;
- twice a day;
- weekly;
- twice a week;
- monthly;
- twice a month;
- custom timezone, time and weekday.

## Test Flow

1. Configure root channel env vars.
2. Configure tenant recipients.
3. Run API.
4. Login as admin.
5. Open settings/integrations.
6. Send a test message.
7. Review notification logs.

## Production Gaps

- Provider credentials and webhook verification must be finalized.
- Retry/dead-letter queue should be backed by a durable queue.
- Delivery receipts should update notification status.
