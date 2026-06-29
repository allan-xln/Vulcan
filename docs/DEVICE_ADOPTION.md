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
- nome;
- e-mail;
- telefone;
- WhatsApp;
- equipe;
- departamento;
- cargo;
- gestor direto;
- perfil;
- preferencias de notificacao;
- opt-in de WhatsApp;
- janela silenciosa;
- política de coleta;
- status de privacidade;
- código de adoção;
- qualidade de coleta.

Quando a adoção cria uma pessoa nova, `telefone`, `WhatsApp`, `whatsapp_enabled`, `whatsapp_opt_in`, tipos de notificacao e janela silenciosa devem ser persistidos no cadastro da pessoa. Quando a adoção vincula um dispositivo a pessoa existente, o Canal WhatsApp Raiz usa o WhatsApp já salvo nessa pessoa.

Se nao houver WhatsApp cadastrado ou opt-in, o Vulcan nao tenta enviar para destino vazio e deve mostrar pendencia operacional.

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
# Adoção de Dispositivo

Quando o agente aparece sem `owner_membership_id`, o dispositivo entra como pendente de adoção.

Campos exibidos:

- hostname;
- usuário do SO;
- sistema operacional;
- versão do agente;
- IP local, quando permitido;
- última comunicação;
- qualidade da coleta;
- código de adoção.

Fluxos suportados:

- vincular a usuário existente;
- criar usuário novo e adotar no mesmo fluxo;
- adoção seca para completar depois;
- trocar equipe;
- trocar política de coleta;
- mover o dispositivo para outro usuário depois.

Após adoção, o dispositivo aparece em hierarquia, métricas, comando e configurações de agentes conforme o escopo do usuário.
