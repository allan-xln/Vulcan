# Wallboards Vulcan

## Rotas

- Geral: `/wallboard`
- Workforce: `/wallboard/workforce`
- Infrastructure: `/wallboard/infra`
- Alias compatível de Infrastructure: `/infra-wallboard`
- Configuração administrativa: `/settings/wallboards`

As rotas usam a mesma autenticação, tenant, permissões e API do Vulcan. A conta de TV
deve possuir papel `read_only`; ela pode consultar os snapshots e não pode alterar
perfis, playlists, tokens de agente ou cadastros.

## Vulcan Command Center

Os dois Wallboards compartilham o `CommandCenterShell`, mas possuem narrativas próprias:

- Workforce: comando geral, pulso operacional, equipes/filiais, aplicações, filiais e
  saúde da coleta.
- Infrastructure: comando geral, topologia, conectividade, Proxmox, servidores, UniFi,
  impressão e saúde da plataforma.

As cenas são construídas com React, GSAP, Motion, ECharts, D3 e Three.js. ECharts e a
topologia 3D são carregados sob demanda. A topologia exibe somente nós e relações
persistidos; links sem ambos os ativos são descartados na visualização e nenhum tráfego é
animado sem `trafficBps` coletado.

O cliente mantém uma única conexão SSE, invalida snapshots por lote, usa polling como
recuperação, fecha o stream quando a aba fica oculta e aplica backoff exponencial com
jitter. O perfil/playlist é revalidado silenciosamente a cada 60 segundos; uma alteração
administrativa entra na TV aberta sem F5 e, se o conteúdo não mudou, a cena corrente não
é reiniciada. O F5 preserva sessão, painel e cena na URL.

## Operação na TV

1. Abra a rota do Wallboard pelo endereço oficial do Vulcan.
2. Entre com a conta somente leitura destinada à TV.
3. Ative tela cheia pelo controle do próprio Wallboard ou pelo navegador.
4. Mantenha a aba aberta. O cliente reconecta o SSE e também faz polling de recuperação.

A interface mostra estado de conexão, horário, última atualização e desloca
periodicamente o conteúdo para reduzir burn-in. Não salva credencial administrativa nem
apresenta controles de mutação.

## Perfis e playlists

O administrador configura em `/settings/wallboards`:

- perfil Workforce ou Infrastructure;
- nome do perfil e identificação física da TV;
- intervalo de atualização;
- tela cheia, tema noturno e prevenção de burn-in;
- resolução-alvo 1080p, 1440p, 4K ou automática;
- preset `auto`, `low`, `balanced`, `cinematic` ou `4k`;
- intensidade visual, movimento, transição e meta de FPS;
- abertura completa/reduzida e duração;
- fallback automático ou 2D obrigatório;
- alert takeover e tempo de permanência;
- ordem e habilitação das cenas;
- rotação da playlist;
- janela de exibição persistida no fuso `America/Sao_Paulo`;
- retorno automático após alerta;
- filial de cada painel;
- duração, visibilidade e ordem.

As mudanças são persistidas em PostgreSQL, isoladas por `tenant_id`, protegidas por RLS e
registradas na auditoria.

O preset recomendado para TV é `auto`. Ele seleciona a capacidade inicial pelo navegador
e reduz a qualidade após quatro amostras abaixo de 65% do FPS-alvo. A recuperação é
gradual após vinte amostras saudáveis. `prefers-reduced-motion`, falta de WebGL, perda de
contexto ou fallback 2D obrigatório sempre vencem o preset visual.

Eventos `critical` e `error` com dados confirmados podem interromper a rotação quando o
perfil e a playlist permitem prioridade. Um evento global aparece mesmo durante a visão
de uma filial; um evento com filial usa o nome persistido do local. O takeover expira no
tempo configurado, pode ser reconhecido na TV e não altera o incidente no backend.

A agenda fica persistida e auditada nesta versão, mas não desliga nem reinicia a TV
automaticamente. Essa limitação é explícita na tela administrativa.

## Origem dos dados

`GET /api/wallboards/snapshot?type=workforce` e
`GET /api/wallboards/snapshot?type=infrastructure` retornam somente dados reais do tenant.
Sem ativos, agentes ou atividade, o Wallboard apresenta estado vazio orientativo. Ele não
preenche KPIs, switches, servidores, pessoas ou incidentes com valores simulados.

Filtros por filial usam `siteId`. O snapshot de Infrastructure agrega inventário,
agentes reais, eventos, incidentes e status das integrações. O snapshot de Workforce
preserva a prioridade sobre atividade e pessoas, cruzando apenas o contexto operacional
que já existe no banco.

Cadastro não equivale a disponibilidade. Um ativo só mantém `online`, `degraded` ou
`offline` no Wallboard quando possui `last_seen_at` nos últimos 30 minutos. Ausência de
observação ou observação mais antiga passa a `unknown` (`sem coleta`), preservando o
status cadastral no inventário. Ativos em manutenção ou aposentados também não entram no
denominador observado.

O score de disponibilidade de Infrastructure é exibido com a fórmula:

```text
(ativos online + 0,5 × ativos degradados)
÷ (ativos online + ativos degradados + ativos offline)
```

O snapshot expõe esse denominador como `monitoredAssets`. Se nenhum ativo possuir estado
confirmado, a disponibilidade é `null` e a TV mostra `Sem coleta`, nunca `0%` ou `100%`.
Métricas não coletadas aparecem como `sem coleta`, `não informado` ou uma orientação
operacional. O Wallboard nunca converte ausência de telemetria em zero saudável.

## Validação visual e soak

E2E de produção:

```bash
cd frontend/web
VULCAN_E2E_BASE_URL=http://192.168.200.4:8099 \
VULCAN_WALLBOARD_TEST_USERNAME='usuario-read-only' \
VULCAN_WALLBOARD_TEST_PASSWORD='definida-fora-do-git' \
corepack pnpm exec playwright test tests/e2e/wallboard.spec.ts --project=chromium
```

O teste cobre autenticação, Workforce, Infrastructure, F5, sessão, 1080p, 1440p, 4K,
ausência de overflow e bloqueio `403` para mutação pela conta read-only.

Teste contínuo:

```bash
cd frontend/web
VULCAN_SOAK_BASE_URL=http://192.168.200.4:8099 \
VULCAN_SOAK_USERNAME='usuario-read-only' \
VULCAN_SOAK_PASSWORD='definida-fora-do-git' \
VULCAN_SOAK_MINUTES=180 \
corepack pnpm test:soak
```

O relatório JSON e as capturas inicial/final são gravados com permissão restrita em
`/tmp`. O script mede heap, CPU aproximada da página, FPS, listeners, timers, canvases,
contextos WebGL, cenas, painéis, conexões SSE, desconexões e erros de console.

Resultado do candidato publicado como `0.5.0`:

- 180 minutos solicitados e 496,18 minutos observados na janela local;
- heap de 7.718.885 para 6.636.526 bytes, pico de 18.575.914 bytes;
- FPS mínimo 8, média 53,5 e máximo 60 no preset adaptativo;
- CPU aproximada da página em 1,29%;
- listeners de 304 para 292, sem crescimento contínuo;
- 14 conexões SSE e nove desconexões forçadas, com reconexão;
- entrada e saída do takeover crítico observadas;
- uma falha transitória de chunk ao tentar carregar recurso durante a queda forçada. A
  amostra otimizada separada recuperou o SSE sem erro de página, e a homologação de
  produção posterior ao reboot terminou com zero erro de console/página.

O caminho Three.js foi homologado separadamente com WebGL/SwiftShader. A perda de
contexto removeu o canvas, reduziu o preset e apresentou a topologia 2D sem erro. Em
hardware sem WebGL, o fallback SVG/2D é a operação esperada.

## Diagnóstico

```bash
curl -fsS http://192.168.200.4:8099/healthz
curl -fsS http://192.168.200.4:8099/readyz
curl -fsS http://192.168.200.4:8099/version
```

No runtime:

```bash
ssh vulcanops@192.168.200.26
cd /opt/vulcan/current
sudo ./healthcheck.sh
sudo ./logs.sh frontend backend edge
```

Falhas de autenticação, SSE ou leitura devem ser investigadas nos logs sem copiar tokens
ou senhas. O Wallboard não deve receber uma conta administrativa como contorno.
