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
- intervalo de atualização;
- tela cheia, tema noturno e prevenção de burn-in;
- rotação da playlist;
- filial de cada painel;
- duração, visibilidade e ordem.

As mudanças são persistidas em PostgreSQL, isoladas por `tenant_id`, protegidas por RLS e
registradas na auditoria.

## Origem dos dados

`GET /api/wallboards/snapshot?type=workforce` e
`GET /api/wallboards/snapshot?type=infrastructure` retornam somente dados reais do tenant.
Sem ativos, agentes ou atividade, o Wallboard apresenta estado vazio orientativo. Ele não
preenche KPIs, switches, servidores, pessoas ou incidentes com valores simulados.

Filtros por filial usam `siteId`. O snapshot de Infrastructure agrega inventário,
agentes reais, eventos, incidentes e status das integrações. O snapshot de Workforce
preserva a prioridade sobre atividade e pessoas, cruzando apenas o contexto operacional
que já existe no banco.

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
