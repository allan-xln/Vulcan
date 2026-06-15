# WhatsApp

O Vulcan possui canal WhatsApp proprio. Ele pode se inspirar em conceitos do LanChat, mas nao altera arquivos, banco ou secrets do LanChat.

## Canal Raiz

```env
ROOT_WHATSAPP_ENABLED=true
ROOT_WHATSAPP_PROVIDER=
ROOT_WHATSAPP_NUMBER=5541984166423
ROOT_WHATSAPP_NAME=Vulcan Notifications
```

Numero inicial: `+55 41 98416-6423`.

Esse numero deve permanecer centralizado em configuracao. Nao hardcodar em telas, seed ou servicos fora da camada de config/env.

## Credenciais De Producao

```env
WHATSAPP_PROVIDER=
WHATSAPP_ACCESS_TOKEN=
WHATSAPP_PHONE_NUMBER_ID=
WHATSAPP_BUSINESS_ACCOUNT_ID=
WHATSAPP_WEBHOOK_VERIFY_TOKEN=
```

Sem credenciais, o provider deve responder `missing_credentials` ou `mocked`. Nunca apresentar isso como envio real.

## Destinatarios

Destinatarios podem ser definidos por:

- tenant;
- usuario;
- equipe;
- cargo/perfil;
- hierarquia;
- destinatario customizado com permissao.

O envio deve respeitar a subarvore do usuario autenticado. Operador nao envia dado de equipe. Supervisor envia apenas para sua equipe/subarvore. Diretor/admin opera no tenant inteiro.

## Tipos Recomendados Para WhatsApp

- insight critico;
- agente offline por mais de X minutos;
- fila offline alta;
- falha de sincronizacao;
- falha de integracao;
- gargalo operacional critico;
- oportunidade de automacao de alto impacto;
- relatorio executivo agendado.

Informativos leves devem ficar no sistema ou em resumo diario, para nao gerar ruido.

## Teste

1. Configure as variaveis raiz.
2. Configure provider/token real ou deixe em mock explicito.
3. Rode backend e frontend.
4. Login `teste/teste`.
5. Abra Notificacoes.
6. Clique em `Testar WhatsApp`.
7. Verifique status em Historico e logs.

Status esperados:

- `sent`/`delivered`: envio real ou confirmado pelo provider;
- `mocked`: simulacao assumida;
- `missing_credentials`: credencial pendente;
- `failed`: provider respondeu erro;
- `queued`/`retrying`: fila ou retentativa.

## Pendencias Para Producao Total

- Definir provider final: WhatsApp Business API, gateway homologado ou sessao local controlada.
- Implementar webhooks de entrega/leitura.
- Criar tabela dedicada de tentativas/receipts para alto volume.
- Validar templates aprovados quando usar API oficial.
