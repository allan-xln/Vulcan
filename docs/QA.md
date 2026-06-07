# QA

Este documento registra o QA do MVP comercial demonstrável.

## Comandos Recomendados

```bash
cd /home/allan/Dev/Vulcan
./scripts/bootstrap.sh
corepack pnpm supabase:validate
corepack pnpm supabase:migrate
corepack pnpm seed:demo
corepack pnpm lint:web
corepack pnpm typecheck:web
corepack pnpm build:web
corepack pnpm dev
```

Testes backend:

```bash
cd /home/allan/Dev/Vulcan
PYTHONPATH=backend/api .venv/bin/python -m pytest backend/api/tests/test_api.py -q
```

Teste visual/e2e:

```bash
cd /home/allan/Dev/Vulcan
corepack pnpm --dir frontend/web test:e2e
```

## Validações Executadas Nesta Rodada

- `corepack pnpm seed:demo`: aprovado.
- `corepack pnpm supabase:validate`: aprovado.
- `corepack pnpm supabase:migrate`: aprovado, migrations reaplicadas de forma idempotente.
- `python3 -m py_compile scripts/seed_demo.py backend/api/app/security.py backend/api/app/repository.py`: aprovado.
- `corepack pnpm lint:web`: aprovado, sem avisos.
- `corepack pnpm --dir frontend/web typecheck`: aprovado.
- `corepack pnpm build:web`: aprovado.
- `PYTHONPATH=backend/api .venv/bin/python -m pytest backend/api/tests/test_api.py -q`: aprovado, 11 testes.
- `corepack pnpm test:web`: aprovado, 1 teste unitário.
- `FRONTEND_PORT=3012 corepack pnpm --dir frontend/web test:e2e`: aprovado, 1 teste Playwright.
- `corepack pnpm demo:validate`: aprovado.
- Validação por API dos perfis `teste`, `diretor`, `coordenador`, `gerente`, `supervisor`, `lider`, `operador1`, `operador2`, `operador3`: aprovada.

Observação: uma primeira tentativa de Playwright em `FRONTEND_PORT=3002` falhou porque havia um servidor Next antigo reaproveitado nessa porta com overlay de runtime do Webpack. A repetição em porta limpa `3012` passou.

## Resultado Da Visibilidade Por Perfil

Após seed, a API retornou os seguintes escopos esperados:

```text
teste: hierarquia 9, dispositivos 11
diretor: hierarquia 8, dispositivos 8
coordenador: hierarquia 7, dispositivos 7
gerente: hierarquia 6, dispositivos 6
supervisor: hierarquia 5, dispositivos 5
lider: hierarquia 4, dispositivos 4
operador1: hierarquia 1, dispositivos 1
operador2: hierarquia 1, dispositivos 1
operador3: hierarquia 1, dispositivos 1
```

## Pontos Corrigidos

- Seed comercial ficou idempotente e preserva dados reais do agente.
- Usuários locais por perfil foram habilitados no backend apenas para desenvolvimento.
- Acesso local agora consulta `memberships` reais para calcular escopo hierárquico.
- Dashboard inicial recebeu métricas executivas profundas, heatmap, rankings, saúde da operação e feed vivo.

## Pendências Reais

- Conectar os botões de simulação comercial a jobs reais do backend.
- Testar pacote Windows em uma máquina Windows real.
- Validar OAuth real de Gmail/Outlook quando credenciais existirem.
- Ativar WhatsApp real quando o provedor for definido e credenciais forem preenchidas.
- Rodar Playwright com frontend/backend já ativos no ambiente final de apresentação.
