# Métricas Operacionais

O Vulcan transforma eventos do agente em métricas para inteligência operacional. O foco é produtividade, gargalos, eficiência, automação e recomendações, sem capturar conteúdo privado.

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
- `agent_error`.

## Métricas Calculadas

- tempo por aplicativo;
- tempo por janela quando permitido por política;
- tempo ativo;
- tempo ocioso;
- tempo analisado;
- tempo fragmentado;
- maior bloco de foco;
- trocas de contexto por hora;
- aplicativos mais usados;
- janelas mais usadas;
- períodos de maior atividade;
- períodos de ociosidade;
- qualidade de coleta;
- estabilidade dos agentes;
- fila offline;
- dispositivos online/offline;
- gargalos por sistema;
- oportunidades de automação;
- economia estimada de horas;
- economia financeira estimada.

## Coleta Limitada

Em GNOME/Wayland, o sistema operacional pode bloquear detalhes finos da janela ativa. Quando isso ocorre, o Vulcan marca a qualidade como `low` ou `blocked_by_os` e mostra o alerta em português. O agente não tenta burlar controles de privacidade.

## Política De Privacidade

O agente não coleta:

- senhas;
- teclas digitadas;
- prints contínuos de tela;
- webcam;
- áudio;
- clipboard irrestrito;
- cookies;
- tokens;
- conteúdo de mensagens privadas;
- documentos pessoais.

Coletas sensíveis como título de janela, URL de navegador e lista de processos dependem de flags explícitas na política do agente.

