# LGPD

## Product Principle

Vulcan mede fluxo operacional, nao conteudo pessoal.

## Collected Data

- active application name;
- active window category when allowed by the OS and policy;
- duration;
- context switch count;
- idle/session status;
- agent heartbeat;
- queue depth and sync status;
- operational events;
- aggregated metrics;
- audit logs.

## Not Collected

- passwords;
- keystrokes;
- audio;
- webcam;
- continuous screenshots;
- private message contents;
- clipboard contents;
- personal files.

## Controls Required Per Tenant

- retention period;
- employee notice/consent text;
- privacy mode flags;
- export and deletion workflow;
- audit trail for admin actions;
- list of enabled collectors;
- list of disabled collectors.

Initial controls are available in Configuracoes > LGPD e privacidade and Configuracoes > Politicas de coleta. They persist in `tenant_settings.settings` and are audited on change.

## Demo Message

Use this wording in sales and onboarding:

`O Vulcan mostra onde a operacao trava, nao o conteudo privado do colaborador.`

## Production Checklist

- Document lawful basis and contract terms.
- Add customer DPA template.
- Add retention enforcement job.
- Add data export flow.
- Add deletion/anonymization flow.
- Add admin audit review.
- Add tenant-level collector flags.
