# Frontend

O frontend do Vulcan fica em `frontend/web` e usa Next.js, Tailwind CSS, Recharts, Lucide icons e Framer Motion.

## Experiência

A interface foi desenhada como uma Central de Inteligência Operacional, não como um painel administrativo comum.

Características atuais:

- sem navbar tradicional;
- navegação por camada de comando em tela cheia;
- login animado com identidade Vulcan;
- dashboard de tempo real;
- métricas operacionais;
- organograma hierárquico;
- dispositivos abaixo de cada usuário na hierarquia;
- insights de IA;
- central de notificações;
- configurações guiadas;
- status de Supabase, IA, WhatsApp e e-mail.

## Idioma

Todos os textos visíveis ao usuário devem ficar em português do Brasil. Nomes técnicos internos podem permanecer em inglês no código, mas labels, botões, mensagens, estados vazios, loading e erros precisam aparecer em português.

## Visual

Tema oficial:

- laranja Vulcan como cor principal;
- fundo preto/cinza escuro;
- contraste alto para leitura;
- glows controlados;
- animações visíveis, mas sem poluir;
- microinterações elegantes;
- sensação de central operacional premium.

Regra de design: o Vulcan deve parecer uma central operacional premium, não uma festa neon.

## Tempo Real

O dashboard mostra indicadores como:

- `Tempo real ativo`;
- `Última sincronização`;
- agentes online;
- qualidade da coleta;
- avisos de coleta limitada pelo sistema operacional;
- cards e telas de métricas/notificações com status ao vivo.

Esses sinais são calculados com base nos dispositivos, métricas e última atualização da API.

## Dashboard Comercial

A tela inicial foi ampliada para demonstrar o Vulcan como produto vendável. Ela inclui:

- KPIs executivos com contagem animada;
- tempo analisado, ativo e ocioso;
- taxa de foco e fragmentação;
- economia estimada em horas e valor financeiro;
- heatmap operacional por horário;
- ranking de aplicativos;
- ranking de usuários;
- setores mais ativos;
- saúde dos agentes;
- feed vivo de notificações, insights e sinais de qualidade;
- botões de simulação comercial preparados para jobs do backend.

Quando os dados forem demonstrativos, a interface exibe `Ambiente demonstrativo`. Quando o usuário estiver em sessão de teste real sem fallback, a tela exibe `Somente dados reais`.

## Autenticação

O frontend suporta Supabase Auth quando as variáveis públicas estão configuradas:

```env
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=
NEXT_PUBLIC_API_URL=http://localhost:3001
```

Fallback local existe apenas para desenvolvimento:

```text
teste / teste
admin / admin
```

## Configurações Guiadas

A tela de configurações possui seções para:

- Geral;
- Empresa;
- Usuários e hierarquia;
- Agentes;
- Supabase;
- Inteligência Artificial;
- WhatsApp;
- E-mail;
- Notificações e recorrências;
- Segurança;
- Integrações.

WhatsApp e e-mail chamam endpoints reais de teste do backend e mostram mensagens claras quando faltam credenciais.

## Hierarquia Com Dispositivos

A tela de Hierarquia cruza usuários (`memberships`) com dispositivos (`devices`) por `ownerMembershipId`. Cada pessoa pode ser expandida para visualizar notebooks/agentes vinculados, qualidade da coleta, fila offline e última sincronização.

Ações preparadas:

- mover dispositivo para outro usuário visível;
- desvincular dispositivo;
- auditoria no backend;
- respeito ao escopo hierárquico do usuário logado.

## Métricas Profundas

A tela de Métricas consome `/operational-intelligence` para mostrar:

- o que está acontecendo agora;
- tempo ativo;
- tempo ocioso;
- taxa de ociosidade;
- trocas de contexto;
- trocas por hora;
- score de foco;
- dispersão operacional estimada;
- maior bloco de foco contínuo;
- tempo fragmentado;
- controle por sistema/aplicativo;
- linha do tempo ativa x ociosa;
- janelas coletadas somente quando a política permitir;
- qualidade de coleta por dispositivo;
- recomendações de IA operacional.

Dispersão operacional estimada não lê conteúdo privado. Ela é calculada por sinais comportamentais permitidos: ociosidade, fragmentação, frequência de troca de contexto e categoria operacional do aplicativo.
