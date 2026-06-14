# Insights Inteligentes

## Objetivo

A tela `Insights` e a central de diagnostico operacional do Vulcan. Ela nao existe para listar dados soltos; ela responde:

- o que esta acontecendo;
- por que isso importa;
- quem ou qual area foi impactada;
- quanto tempo ou dinheiro pode estar sendo perdido;
- qual acao deve ser tomada agora;
- qual metrica sustenta o diagnostico.

O tom deve ser construtivo. O Vulcan mede fluxo operacional, nao conteudo pessoal.

## Escopo Por Hierarquia

Todos os insights retornados pelo backend passam pelo contexto autenticado, tenant e filtro de hierarquia.

- Operador: apenas insights pessoais.
- Lider: propria visao e operadores abaixo.
- Supervisor: subarvore operacional.
- Gerente: supervisores, lideres e operadores abaixo.
- Coordenador: gerentes, supervisores, lideres e operadores abaixo.
- Diretor/admin: visao agregada do tenant.
- Root: todos os tenants, quando habilitado pelo contexto de acesso.

A IA de aprofundamento usa o mesmo insight retornado pelo backend. Se o usuario pedir algo fora da hierarquia, a resposta deve negar o acesso em linguagem simples.

## Tipos De Insight

Tipos usados na demo e preparados no contrato:

- produtividade;
- ociosidade;
- foco;
- troca de contexto;
- gargalo operacional;
- automacao sugerida;
- risco operacional;
- agente offline;
- coleta limitada;
- equipe sobrecarregada;
- desvio de padrao;
- eficiencia por equipe;
- economia estimada;
- tendencia positiva;
- tendencia negativa;
- relatorio executivo;
- recomendacao de treinamento;
- recomendacao de processo;
- recomendacao de integracao.

## Campos Principais

`GET /insights` retorna cards ricos com:

- `scopeType`, `scopeId`, `targetUserId`, `targetTeamId` e `targetDepartmentId`;
- `roleVisibility`;
- `insightType`;
- `title`, `summary`, `diagnosis` e `recommendation`;
- `evidence` e `metricsUsed`;
- `affectedUsers` e `affectedTeams`;
- `severity`, `impactLevel` e `confidence`;
- `estimatedTimeLoss`, `estimatedCostLoss` e `estimatedSavings`;
- `periodStart` e `periodEnd`;
- `status`;
- `sentToWhatsapp`, `sentToEmail`, `whatsappStatus`, `emailStatus` e `lastSentAt`;
- `suggestedQuestions`;
- `actionStatus`.

Hoje esses campos usam a tabela `ai_insights` com `metadata` JSONB para evitar migracao destrutiva. Uma etapa futura pode normalizar os campos mais usados em colunas dedicadas.

## Tela

A experiencia visual e dividida em:

- header com tempo real, botao de gerar insight e atualizar;
- mini dashboard com criticos, automacoes e economia potencial;
- status de WhatsApp/e-mail;
- distribuicao por severidade e tipo;
- filtros por periodo, tipo, severidade, status, equipe, usuario e envio;
- cards acionaveis com economia, confianca, envio e status;
- painel de detalhe com diagnostico, evidencias, escopo, perguntas sugeridas, IA e acoes.

Cada insight pode:

- abrir Metricas ja filtrada;
- aprofundar com IA;
- enviar por WhatsApp;
- enviar por e-mail;
- copiar resumo;
- criar plano de acao;
- marcar como resolvido.

## IA

O fluxo preparado e:

1. Eventos reais entram pelo agente.
2. Metricas sao agregadas.
3. Regras deterministicas detectam padroes.
4. Llama classifica e resume sinais operacionais quando configurado.
5. GPT aprofunda insights executivos quando configurado.
6. O insight fica salvo e auditavel.

No estado atual, `POST /insights/{id}/ask` usa fallback explicito `rules_fallback_explicit` quando nao ha provedor real conectado. Isso nao deve ser apresentado como GPT real.

## WhatsApp E E-mail

Os botoes de envio usam os servicos centrais de notificacao do Vulcan. O status volta para o insight:

- `sent`;
- `queued`;
- `mock`;
- `disabled`;
- `failed`;
- `not_sent`.

O numero raiz de WhatsApp deve vir de configuracao (`ROOT_WHATSAPP_*`), nunca hardcoded no card.

## Planos De Acao

`POST /insights/{id}/create-action` registra uma acao vinculada ao insight no metadata:

- titulo;
- responsavel;
- prioridade;
- prazo;
- observacao;
- status inicial `open`.

Uma tabela dedicada de acoes e recomendada antes de SaaS enterprise self-service.

## Endpoints

- `GET /insights`
- `GET /insights/{id}`
- `POST /insights/generate`
- `POST /insights/{id}/ask`
- `POST /insights/{id}/send-whatsapp`
- `POST /insights/{id}/send-email`
- `POST /insights/{id}/resolve`
- `POST /insights/{id}/create-action`

## Validacao Manual

1. Entrar como `teste / teste`.
2. Abrir `Insights`.
3. Validar mini dashboard, filtros e cards.
4. Clicar em um insight.
5. Abrir Metricas relacionadas.
6. Perguntar algo no painel `Aprofundar com IA`.
7. Enviar WhatsApp/e-mail e conferir status.
8. Criar plano de acao.
9. Marcar como resolvido.
10. Repetir com `operador1`, `lider`, `supervisor`, `gerente`, `coordenador` e `diretor` para validar escopo.

## Pendencias Para Producao Total

- Conectar `ask` ao roteador GPT/Llama com controle de custo e timeout.
- Normalizar plano de acao em tabela dedicada.
- Criar agendador de insights diario/semanal/mensal.
- Salvar destinatarios reais por tenant e usuario no envio direto do insight.
- Criar testes automatizados por perfil hierarquico.
