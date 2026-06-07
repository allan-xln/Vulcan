# Demo Comercial Vulcan

Esta demo foi criada para mostrar o Vulcan como uma Central de Inteligência Operacional com IA, pronta para apresentação comercial e testes de hierarquia.

## Objetivo

A demo permite demonstrar:

- dashboard executivo em tempo real;
- métricas operacionais por usuário, setor, dispositivo e aplicativo;
- hierarquia dinâmica com visibilidade por subárvore;
- dispositivos Windows, Linux e macOS simulados;
- coexistência com agente real instalado no notebook;
- insights de IA, notificações e oportunidades de automação;
- usuários de teste por nível hierárquico.

## Como Gerar

```bash
cd /home/allan/Dev/Vulcan
corepack pnpm seed:demo
```

O comando é idempotente para os dados demonstrativos. Ele remove e recria apenas registros marcados com `metadata.seed = vulcan-demo`, preservando dados reais enviados pelo agente.

## Tenant Demo

```text
Nome: Vulcan Demo
tenant_id: 00000000-0000-0000-0000-000000000301
```

## Usuários De Teste

Todos os usuários abaixo funcionam no fallback local de desenvolvimento:

```text
teste / teste
diretor / diretor
coordenador / coordenador
gerente / gerente
supervisor / supervisor
lider / lider
operador1 / operador1
operador2 / operador2
operador3 / operador3
```

Também existem e-mails locais equivalentes:

```text
teste@vulcan.local
diretor@vulcan.local
coordenador@vulcan.local
gerente@vulcan.local
supervisor@vulcan.local
lider@vulcan.local
operador1@vulcan.local
operador2@vulcan.local
operador3@vulcan.local
```

O Supabase Auth real continua sendo o caminho de produção. O fallback local existe apenas fora de produção.

## Hierarquia

```text
teste / Root Demo
└── Diretor Operacional
    └── Coordenador de Operações
        └── Gerente Operacional
            └── Supervisor de Faturamento
                └── Líder Operacional
                    ├── Operador 1
                    ├── Operador 2
                    └── Operador 3
```

Visibilidade esperada:

- `teste`: vê toda a empresa demo.
- `diretor`: vê diretor e toda a árvore abaixo.
- `coordenador`: vê coordenador, gerente, supervisor, líder e operadores.
- `gerente`: vê gerente, supervisor, líder e operadores.
- `supervisor`: vê supervisor, líder e operadores.
- `lider`: vê líder e operadores.
- `operador1`, `operador2`, `operador3`: veem apenas seus próprios dados.

## Dispositivos Simulados

A demo cria dispositivos com status e qualidade de coleta variados:

- `WIN-ADM-001`
- `WIN-FIN-002`
- `WIN-OPER-003`
- `WIN-FAT-004`
- `WIN-LIDER-005`
- `LINUX-ALLAN-NB`
- `LINUX-SUPORTE-001`
- `LINUX-LOG-002`
- `MACBOOK-GERENCIA-001`
- `MACBOOK-DIRETORIA-001`

Cada dispositivo possui hostname, sistema operacional, versão do agente, usuário vinculado, status online/offline, fila offline e qualidade de coleta.

## Dados Operacionais

O seed gera eventos para hoje, últimos 7 dias e últimos 30 dias com variação realista:

- uso de ERP;
- WhatsApp Web;
- navegador;
- Excel;
- Outlook;
- Teams;
- sistema interno;
- terminal;
- VS Code;
- sistema financeiro;
- sistema logístico;
- CRM;
- períodos ociosos;
- troca de contexto;
- gargalos simulados;
- agentes offline;
- coleta limitada em alguns ambientes.

## IA E Notificações

A demo inclui insights com título, resumo, severidade, impacto, recomendação, escopo, período e economia estimada. Também cria notificações por sistema, agente, WhatsApp e e-mail com status de envio ou credenciais pendentes.

## Modo Demo Na Interface

O dashboard mostra o badge `Ambiente demonstrativo` quando dados de fallback/demo podem aparecer. Dados reais do agente continuam aparecendo quando existirem no Supabase para o mesmo tenant.

## Teste Rápido Por API

```bash
TOKEN=$(curl -sS -H "Content-Type: application/json" \
  -d '{"username":"gerente","password":"gerente"}' \
  http://localhost:3001/auth/login | python3 -c 'import sys,json; print(json.load(sys.stdin)["accessToken"])')

curl -sS \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Tenant-Id: 00000000-0000-0000-0000-000000000301" \
  http://localhost:3001/operational-intelligence | python3 -m json.tool
```
