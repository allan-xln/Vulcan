# Canal WhatsApp Raiz

O Canal WhatsApp Raiz e o numero emissor central do Vulcan. Ele envia metricas, alertas, insights, relatorios e notificacoes automaticas para usuarios finais dos tenants.

Clientes nao precisam conectar o proprio WhatsApp no MVP. Eles configuram destinatarios, preferencias, frequencia e escopo.

## Numero Mestre

Configuracao:

```env
ROOT_WHATSAPP_ENABLED=true
ROOT_WHATSAPP_PROVIDER=evolution
ROOT_WHATSAPP_NUMBER=
ROOT_WHATSAPP_NAME=Vulcan Notifications
ROOT_WHATSAPP_MOCK_MODE=false
```

O numero deve estar em E.164 somente com digitos, por exemplo `55DDDNUMERO`. O backend valida o numero quando o canal esta ativo. A tela `Configuracoes -> WhatsApp` mostra `Numero mestre do Vulcan` e nao marca conectado se a Evolution estiver desconectada.

## Destinatarios

Fonte dos numeros:

1. `memberships.whatsapp`;
2. cadastro/edicao da pessoa;
3. cadastro feito durante adocao do dispositivo;
4. preferencias de notificacao.

Se o colaborador for criado pela adocao, telefone/WhatsApp e opt-in devem ir para o cadastro da pessoa. Se o dispositivo for vinculado a usuario existente, o envio usa o numero desse usuario.

Sem numero ou sem opt-in, o item fica fora do envio e deve aparecer como pendencia operacional: usuario sem WhatsApp cadastrado ou opt-in pendente.

Campos LGPD/preferencia em `memberships`:

- `whatsapp_enabled`;
- `whatsapp_opt_in`;
- `whatsapp_notification_types`;
- `quiet_hours_start`;
- `quiet_hours_end`.

## Hierarquia E Permissao

O resolver de destinatarios respeita `tenant_id`, `membership_closure`, escopo do usuario autenticado e preferencias:

- diretor/admin: visao geral do tenant;
- coordenador/gerente: areas abaixo;
- supervisor/lider: equipe/subarvore;
- colaborador: apenas metricas pessoais basicas;
- TI/admin: alertas tecnicos de agentes e integracoes.

Operador nao recebe dados de outro colaborador. Supervisor nao recebe fora da sua subarvore. Nenhum tenant enxerga destinatario de outro tenant.

## Templates

Templates iniciais do Canal Raiz:

- metrica pessoal;
- resumo da equipe;
- resumo executivo;
- insight critico;
- agente offline;
- dispositivo aguardando adocao;
- oportunidade de automacao;
- relatorio diario;
- relatorio semanal;
- falha de integracao.

Mensagens para colaboradores devem ser construtivas, sem tom punitivo e sem exposicao indevida.

## Fila E Auditoria

Tabela principal: `whatsapp_delivery_queue`.

Campos importantes:

- `tenant_id`;
- `recipient_membership_id`;
- `destination`;
- `provider`;
- `provider_instance`;
- `notification_type`;
- `template_id`;
- `payload`;
- `status`;
- `attempts`;
- `max_attempts`;
- `last_error`;
- `provider_message_id`;
- `idempotency_key`;
- `scheduled_for`;
- `next_attempt_at`;
- `sent_at`;
- `delivered_at`;
- `dead_letter_at`.

Cada tentativa grava `whatsapp_delivery_logs`. O endpoint de retry reabre item falho sem duplicar a mensagem original. `idempotency_key` evita duplicidade por notificacao/destinatario.

## Fallback

Quando WhatsApp falha definitivamente, o backend prepara fallback:

- in-app, via `notifications`;
- e-mail, quando o canal estiver configurado.

O fallback tambem registra metadata e auditoria. Nao ha promessa de "nunca cair"; ha degradacao segura e visivel.

## Como Testar

```bash
cd /home/allan/Documentos/ProjetosLanFuture/Vulcan

./scripts/start-all.sh
./scripts/status-all.sh
```

Na UI:

1. Entrar como `teste / teste`.
2. Abrir `Configuracoes -> WhatsApp`.
3. Salvar numero mestre, provider e API key.
4. Ver QR e conectar.
5. Enviar teste para um numero autorizado.
6. Abrir `Notificacoes`.
7. Processar/reabrir fila se necessario.

Via API:

```bash
curl -H "Authorization: Bearer dev-vulcan-admin-token" \
  -H "X-Tenant-Id: 00000000-0000-0000-0000-000000000301" \
  http://localhost:3001/integrations/whatsapp/root/recipients
```
