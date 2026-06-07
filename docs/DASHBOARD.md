# Dashboard

O dashboard inicial do Vulcan é a Central de Inteligência Operacional. Ele foi desenhado para apresentar valor em menos de 60 segundos para supervisores, gerentes, coordenadores, diretores e administradores.

## Sinais Visuais

- `Tempo real ativo`;
- `Última sincronização`;
- quantidade de agentes online;
- badge `Ambiente demonstrativo` quando a sessão usa dados demo;
- indicadores de fila offline, coleta limitada e notificações pendentes.

## KPIs Executivos

A primeira tela consolida:

- usuários ativos agora;
- eventos processados;
- gargalos detectados;
- insights de IA;
- potencial de automação;
- tempo analisado;
- tempo ativo;
- tempo ocioso;
- taxa de foco;
- índice de fragmentação;
- trocas de contexto;
- dispositivos online/offline;
- qualidade de coleta;
- fila offline;
- economia financeira estimada;
- notificações enviadas e pendentes.

## Componentes

- cards de KPI animados;
- painel `Pulso executivo da operação`;
- gráfico de fluxo operacional;
- heatmap operacional por horário;
- grade de agentes conectados em tempo real;
- ranking de aplicativos;
- ranking de usuários;
- setores mais ativos;
- feed vivo de sinais;
- painel de saúde da operação;
- feed de insights de IA;
- central de notificações.

## Dados Reais Versus Demo

O Vulcan nunca apresenta mock oculto como se fosse produção. O dashboard usa:

- dados reais quando vierem do Supabase/agente;
- dados demo quando o seed foi gerado;
- fallback visual apenas quando `allowDemoFallback` está ativo.

Quando uma sessão for somente real, o dashboard exibe `Somente dados reais`.

## Ações De Demonstração

A tela possui botões para:

- atualizar simulação;
- gerar novo insight;
- simular agente online/offline;
- simular alerta crítico.

Nesta versão, os botões são ações visuais de demonstração preparadas para serem conectadas a jobs backend em produção.

