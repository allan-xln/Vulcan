# Adoção De Dispositivos

O fluxo de adoção conecta um agente instalado a uma pessoa, equipe e política de coleta.

Mensagem central: o Vulcan mede fluxo operacional, nao conteudo pessoal.

## Fluxos Suportados

1. Adoção por token no instalador.
2. Adoção manual no painel.
3. Adoção seca para completar depois.

## Como O Dispositivo Aparece

Quando o agente faz `POST /agent/enroll` sem `membershipId`, o backend registra o dispositivo com:

- `owner_membership_id = null`;
- `metadata.adoptionStatus = pending`;
- `metadata.adoptionCode`;
- hostname;
- usuario do sistema;
- SO;
- versao do agente;
- IP local quando disponivel;
- qualidade de coleta.

O gestor/admin vê esse item em `Dispositivos aguardando adoção`.

## Endpoints

- `GET /devices/pending-adoption`
- `POST /devices/{id}/adopt`
- `POST /devices/{id}/link-user`
- `POST /devices/{id}/unlink-user`
- `POST /devices/{id}/move`
- `POST /agent/enroll`
- `POST /agent/heartbeat`
- `POST /agent/events`
- `POST /agent/sync`
- `GET /agent/status`

Todos respeitam tenant e escopo de hierarquia. Adoções gravam `audit_log`.

## Pela Interface

1. Abra `Hierarquia`.
2. Vá em `Dispositivos aguardando adoção`.
3. Escolha a pessoa.
4. Escolha a equipe.
5. Clique em `Adotar`.

Depois disso:

- dispositivo some da fila de pendentes;
- aparece abaixo da pessoa na Hierarquia;
- passa a alimentar Métricas;
- entra no Comando em saúde dos agentes.

## Campos De Adoção

- pessoa ou usuário existente;
- equipe;
- política de coleta;
- status de privacidade;
- código de adoção;
- qualidade de coleta.

## Auditoria

Cada adoção registra:

- quem adotou;
- quando;
- dispositivo;
- pessoa vinculada;
- equipe;
- política;
- dono anterior, se existia.

## Limitações Atuais

- criação de usuário dentro do modal de adoção ainda deve ser conectada à UI; o backend já aceita `mode=new_user`.
- botão `ignorar temporariamente` ainda não foi exposto na interface.
- app/tray macOS e Windows completo ainda são próximos passos de produto.
