# Privacy

## Trust Boundary

Vulcan must never feel like spyware. Every product screen should reinforce operational measurement, scoped access and clear configuration.

## Employee-Facing Explanation

Vulcan records operational signals from work devices to help the company identify bottlenecks, overloaded teams, slow systems and automation opportunities. It does not collect passwords, keystrokes, audio, webcam, private message content or continuous screenshots.

## Manager-Facing Explanation

Managers receive aggregated operational intelligence: active time, idle time, app categories, agent health, context switches, bottlenecks, alerts and recommendations. Access is limited by tenant and hierarchy.

## Recommended UI Copy

`Modo privacidade ativo: o Vulcan mede fluxo operacional e qualidade de coleta. Conteudo pessoal nao e monitorado.`

## Data Retention

Recommended defaults for pilots:

- raw operational events: 90 days;
- aggregated metrics: 18 months;
- audit logs: 24 months;
- AI prompts/responses: disabled by default unless explicitly needed for audit.

The Settings screen exposes privacy controls for consent, user pause, export enablement, anonymization days and collection toggles. Riskier collectors such as browser URL and screenshots remain blocked by backend validation in the MVP.

## Open Items

- Enforce retention jobs in production.
- Expand tenant-level privacy policy editor.
- Add employee consent export.
- Connect per-collector toggles to remote agent policy rollout.
