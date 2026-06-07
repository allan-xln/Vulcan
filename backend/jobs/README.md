# Jobs Service

Deterministic background jobs for operational event processing.

## Current scope
- normalize accepted raw operational event intake into deterministic operational events
- preserve one-to-one traceability from normalized facts back to raw intake
- keep replay safe behavior by relying on unique `raw_operational_event_intake_id`
- derive deterministic session slices, idle windows and application usage facts from normalized events
- derive deterministic daily operational metrics from operational facts

## Local run
```bash
source .env
source .venv/bin/activate
python backend/jobs/app/run_normalizer.py --tenant-id 00000000-0000-0000-0000-000000000301 --batch-limit 500
python backend/jobs/app/run_operational_facts.py --tenant-id 00000000-0000-0000-0000-000000000301
python backend/jobs/app/run_daily_metrics.py --tenant-id 00000000-0000-0000-0000-000000000301
```
