# Metricas Operacionais

A tela `Metricas` e o centro analitico do Vulcan. Ela existe para investigar causas, comparar recortes, exportar evidencias e transformar sinais operacionais em decisao.

Regra principal: Metricas nao e Comando. Tudo que exige filtro, tabela, comparacao, ranking ou investigacao fica aqui.

## Eventos De Entrada

Eventos aceitos no MVP:

- `app_focus_started`;
- `app_focus_ended`;
- `foreground_application_usage`;
- `foreground_application_change`;
- `context_switch`;
- `idle_started`;
- `idle_ended`;
- `session_locked`;
- `session_unlocked`;
- `user_logged_in`;
- `user_logged_out`;
- `machine_sleep`;
- `machine_resume`;
- `heartbeat`;
- `sync_status`;
- `collection_quality`;
- `agent_error`;
- `agent_health`.

## Filtros

Filtros da tela:

- periodo;
- equipe;
- usuario;
- supervisor responsavel;
- departamento;
- cargo;
- dispositivo;
- sistema operacional;
- categoria;
- status do agente;
- tipo de metrica;
- aplicativo.

Todos os graficos, rankings, tabela e exportacoes usam o mesmo query string enviado para `GET /metrics/detailed` e `GET /metrics/export`.

## Tipos De Metrica

O filtro `metricType` aceita:

- `productive`;
- `idle`;
- `context_switch`;
- `agent`;
- `improductive`.

O backend traduz esses tipos para eventos e categorias equivalentes.

## Graficos Obrigatorios

1. Velocimetro de saude operacional

- SVG customizado;
- ponteiro animado;
- score de 0 a 100;
- composicao por agentes online, foco, ociosidade, trocas e sinais criticos.

2. Donut de distribuicao de tempo

Categorias:

- produtivo;
- ocioso;
- comunicacao;
- sistemas internos;
- navegacao;
- outros.

3. Barras horizontais de apps mais usados

Ranking por minutos no recorte filtrado.

4. Linha temporal de produtividade

Mostra minutos produtivos, ociosos e trocas de contexto por janela de tempo.

5. Heatmap por hora e dia

Mostra concentracao de atividade e trocas por faixa horaria.

6. Ranking de equipes

Agrupa tempo ativo por equipe/departamento.

7. Ranking de usuarios

Agrupa tempo ativo por usuario.

8. Grafico de troca de contexto

Mostra volume de alternancias por janela temporal.

9. Status dos agentes por SO

Agrupa online, sincronizando, offline e pendente por familia de sistema operacional.

10. Qualidade de coleta por sistema

Agrupa coleta alta, media, baixa e bloqueada por SO.

## Metricas Calculadas

- tempo ativo;
- tempo ocioso;
- tempo produtivo;
- tempo improdutivo configuravel;
- foco operacional;
- indice de fragmentacao;
- troca de contexto por hora;
- tempo por app;
- tempo por equipe;
- tempo por usuario;
- tempo por dispositivo;
- uso por sistema operacional;
- agentes online/offline;
- fila pendente dos agentes;
- qualidade de coleta;
- gargalos por app;
- gargalos por equipe;
- oportunidades de automacao;
- economia estimada em horas;
- economia estimada em dinheiro;
- ranking de apps;
- ranking de equipes;
- ranking de usuarios;
- tendencia temporal;
- heatmap por horario;
- alertas por periodo.

## Formula Do Score

O velocimetro combina:

- percentual de agentes online;
- score de foco;
- baixa ociosidade;
- baixa troca de contexto;
- ausencia de sinais criticos.

Formula aplicada no frontend:

```text
score = online*0.28 + foco*0.30 + baixa_ociosidade*0.18 + baixa_troca*0.14 + sinais_ok*0.10
```

Faixas:

- `0 a 53`: Critico;
- `54 a 73`: Atencao;
- `74 a 87`: Saudavel;
- `88 a 100`: Excelente.

## Exportacao

Leia `docs/EXPORTS.md`.

CSV e Excel respeitam os filtros atuais. PDF, e-mail e WhatsApp estao preparados na interface e dependem dos modulos reais de relatorio/canal.

## Dados Reais Versus Demo

Se nao houver filtro analitico e existir seed/demo, a tela pode exibir dados demo sinalizados. Se um filtro retorna vazio, a tela mostra estado sem resultado, sem substituir por dado global.

## Coleta Limitada

Em GNOME/Wayland e outros ambientes restritos, o sistema operacional pode bloquear detalhes finos da janela ativa. Quando isso ocorre, o Vulcan marca a qualidade como `low` ou `blocked_by_os` e exibe o estado correspondente.

## Privacidade

O agente nao coleta:

- senhas;
- teclas digitadas;
- prints continuos;
- webcam;
- audio;
- clipboard irrestrito;
- cookies;
- tokens;
- conteudo de mensagens privadas;
- documentos pessoais.

Coletas sensiveis como titulo de janela, URL de navegador e lista de processos dependem de politica explicita.
