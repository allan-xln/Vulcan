# Dashboard

O dashboard do Vulcan foi separado em duas finalidades:

- `Comando`: acompanhamento executivo, enxuto e em tempo quase real.
- `Metricas`: investigacao analitica profunda, filtravel e exportavel.

Essa separacao evita que a primeira tela vire relatorio e evita que a area analitica fique rasa demais.

## Comando

Leia `docs/COMMAND_CENTER.md`.

Resumo:

- tela para TV, supervisor, gerente e empresario;
- leitura em ate 5 segundos;
- status geral, velocimetro principal, ate seis KPIs, recomendacao da IA e alertas essenciais;
- sem tabelas grandes, rankings longos ou exportacoes;
- clique em sinais importantes abre `Metricas` com filtro aplicado.

## Metricas

Leia `docs/METRICS.md`.

Resumo:

- area de investigacao;
- filtros por periodo, equipe, usuario, departamento, cargo, supervisor, dispositivo, sistema operacional, aplicativo, categoria, status do agente e tipo de metrica;
- graficos analiticos, tabela detalhada e exportacoes;
- todos os graficos usam o mesmo recorte filtrado.

## Bibliotecas Usadas

O frontend reaproveita o stack existente:

- Recharts para linhas, barras, pizza/donut e responsividade;
- Tremor para tabela, badges e base visual;
- Framer Motion para animacoes suaves;
- SVG customizado para o velocimetro principal.

Nao foi adicionada biblioteca pesada de graficos. A escolha reduz risco de bundle, evita duplicar motores visuais e melhora manutencao.

## Estados De Dados

O dashboard distingue:

- dados reais vindos da API/agente;
- dados demo vindos do seed;
- fallback visual apenas quando o modo demo permite.

Quando filtros analiticos retornam vazio, `Metricas` mostra estado sem resultado em vez de preencher com resumo global.
