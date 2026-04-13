# Jobs Service

Deterministic background jobs for telemetry processing.

## Current scope
- normalize accepted raw telemetry intake into deterministic operational events
- preserve one-to-one traceability from normalized facts back to raw intake
- keep replay safe behavior by relying on unique `raw_telemetry_intake_id`
- derive deterministic session slices, idle windows and application usage facts from normalized events
- derive deterministic daily operational metrics from operational facts

## Local run
```bash
source .env
source .venv/bin/activate
python services/jobs/app/run_normalizer.py --batch-limit 500
python services/jobs/app/run_operational_facts.py
python services/jobs/app/run_daily_metrics.py
```
