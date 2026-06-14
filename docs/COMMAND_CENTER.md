# Comando

A tela `Comando` e a central operacional executiva do Vulcan. Ela foi redesenhada para ficar aberta em TV, mesa de supervisor ou rotina de acompanhamento rapido.

Regra principal: Comando nao e Metricas. Comando responde em poucos segundos se a operacao esta saudavel agora.

## Objetivo

- leitura em ate 5 segundos;
- poucos blocos, alta clareza;
- decisao executiva sem investigacao longa;
- alerta apenas quando existe risco operacional relevante;
- navegacao direta para `Metricas` quando algo precisa ser investigado.

## O Que Fica Na Tela

1. Status geral

- tempo real ativo;
- ultima atualizacao;
- status dos agentes;
- status da IA;
- status das notificacoes.

2. Saude Operacional

O bloco central usa um velocimetro SVG proprio, responsivo e animado. O score considera:

- agentes online;
- foco operacional;
- baixa ociosidade;
- baixa troca de contexto;
- ausencia de sinais criticos;
- estabilidade de sincronizacao e qualidade dos dados.

Faixas:

- `0 a 53`: Critico;
- `54 a 73`: Atencao;
- `74 a 87`: Saudavel;
- `88 a 100`: Excelente.

3. KPIs essenciais

A tela fica limitada a seis KPIs:

- agentes online;
- usuarios ativos;
- gargalos criticos;
- foco operacional;
- economia estimada;
- alertas abertos.

4. Acao recomendada agora

Card unico de recomendacao operacional. A mensagem vem dos insights e da inteligencia operacional calculada.

5. Alertas essenciais

Lista curta com os alertas mais importantes. Nao e feed historico.

6. Filtro rapido por equipe

Filtro discreto para `Toda empresa` ou equipes cadastradas. Ele ajusta a leitura operacional sem transformar Comando em area analitica.

## O Que Foi Removido De Comando

Foram retirados da tela principal:

- tabelas grandes;
- rankings extensos;
- multiplos graficos analiticos;
- historico longo;
- analise por usuario;
- analise por aplicativo;
- exportacoes;
- comparacoes complexas;
- feed vivo grande.

Esses itens pertencem a `Metricas`.

## Navegacao Para Metricas

Itens clicaveis no Comando abrem `Metricas` com filtro aplicado:

- agente offline abre filtro `agentStatus=offline`;
- dispositivo especifico abre filtro por `deviceId`;
- equipe em alerta abre filtro por `teamId`;
- ociosidade abre filtro `metricType=idle`;
- gargalo por app abre filtro `app`;
- troca de contexto abre filtro `metricType=context_switch`.

Essa ponte preserva a diferenca entre acompanhar e investigar.

## Estados

Comando usa estados seguros para:

- dados reais;
- dados demo sinalizados;
- agente offline;
- coleta limitada;
- notificacoes pendentes;
- ausencia de dados.

Mock ou fallback visual nunca deve aparecer como dado real.
