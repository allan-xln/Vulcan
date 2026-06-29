# Hierarquia

A hierarquia do Vulcan é dinâmica e não possui limite fixo de níveis. Ela usa `memberships` como vínculo do usuário dentro do tenant e `membership_closure` para consulta eficiente da árvore.

## Modelo

- `tenants`: empresa cliente.
- `user_profiles`: identidade de usuário.
- `roles`: papel e escopo de permissão.
- `memberships`: vínculo do usuário com tenant, cargo, departamento e gestor direto.
- `membership_closure`: tabela de fechamento para consultar ancestrais e descendentes.
- `devices`: dispositivos vinculados a um `owner_membership_id`.

## Escopos

- `self`: usuário vê apenas seus próprios dados.
- `subtree`: usuário vê seus próprios dados e subordinados.
- `tenant`: administrador vê tudo dentro da empresa.
- `global/root`: operador Vulcan vê todos os tenants, quando habilitado.

## Demo

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

## Dispositivos Na Hierarquia

A tela de Hierarquia mostra notebooks/agentes abaixo de cada pessoa:

- contador de dispositivos;
- status online/offline/sincronizando;
- última sincronização;
- fila offline;
- qualidade de coleta;
- versão do agente;
- ação para mover dispositivo para outro usuário;
- ação para desvincular dispositivo.

Toda alteração de dono do dispositivo passa pelo backend e respeita `tenant_id`.

## CRUD Comercial

A tela permite:

- criar usuário abaixo de um gestor visível;
- editar nome, cargo, e-mail, usuário, senha opcional, telefone e WhatsApp;
- excluir usuário, fechando a árvore ao religar subordinados ao gestor acima;
- mover dispositivo para uma pessoa;
- desvincular dispositivo;
- adotar dispositivo pendente e vincular a pessoa/equipe.

O cadastro respeita a pirâmide. Um diretor cria níveis abaixo dele, supervisor cria líder/monitor/usuário e operador não recebe permissão de gestão.

## Equipes

Equipe é agrupamento operacional e não substitui hierarquia.

Exemplos:

- Financeiro;
- Operação;
- Administrativo;
- Suporte;
- Comercial;
- Logística.

A equipe aparece na adoção do dispositivo, nos filtros de Comando/Métricas e no detalhamento exportável.

## Regras De Visibilidade Da Demo

- `teste`: toda a empresa.
- `diretor`: diretor e árvore abaixo.
- `coordenador`: coordenador e árvore abaixo.
- `gerente`: gerente e árvore abaixo.
- `supervisor`: supervisor e árvore abaixo.
- `lider`: líder e operadores.
- `operador1`, `operador2`, `operador3`: apenas seus próprios dados.
# Hierarquia ERS

Hierarquia operacional esperada no piloto:

```text
ERS
-> Diretor
-> Coordenador
-> Gerente
-> Supervisor
-> Líder
-> Operador/Colaborador
```

Perfis com escopo `tenant` veem todo o tenant. Perfis com escopo `hierarchy` veem a própria subárvore via `membership_closure`. Perfis com escopo `self` veem somente o próprio membership/dispositivo/métricas.

Ao criar ou editar uma pessoa no painel, defina:

- superior direto;
- nível na pirâmide;
- perfil/permissão;
- departamento;
- contato;
- equipe, quando aplicável;
- dispositivo vinculado, quando aplicável.

Mudanças de superior, cargo, equipe e perfil recalculam a árvore com `vulcan_refresh_membership_closure`.
