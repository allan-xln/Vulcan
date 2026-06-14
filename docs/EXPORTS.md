# Exportacoes

A tela `Metricas` concentra exportacoes do recorte analitico atual. Toda exportacao deve respeitar tenant, hierarquia, permissoes e filtros visiveis na interface.

## Formatos

Formatos atuais:

- CSV;
- CSV compativel com Excel.

Formatos preparados na interface:

- PDF;
- envio por e-mail;
- envio por WhatsApp.

PDF, e-mail e WhatsApp dependem do modulo de relatorios/canais reais estar configurado para producao.

## Endpoint

```http
GET /metrics/export
```

Parametros aceitos:

- `format`: `csv` ou `excel`;
- `period`;
- `teamId`;
- `membershipId`;
- `deviceId`;
- `supervisorId`;
- `department`;
- `title`;
- `os`;
- `category`;
- `agentStatus`;
- `metricType`;
- `app`.

Headers:

```text
Authorization: Bearer <token>
X-Tenant-Id: <tenant_id>
```

## Conteudo Exportado

O arquivo inclui:

- data/hora da exportacao;
- periodo;
- filtros aplicados;
- usuario;
- cargo;
- supervisor;
- equipe;
- departamento;
- dispositivo;
- sistema operacional;
- status do agente;
- aplicativo;
- categoria;
- evento;
- duracao em segundos;
- qualidade de coleta.

## Excel

O botao `Exportar Excel` gera arquivo CSV compativel com Excel e BOM UTF-8. Isso preserva acentos em ambiente local sem adicionar dependencia pesada ao frontend.

## Privacidade

Exportacoes carregam apenas metadados operacionais autorizados. O Vulcan nao exporta senhas, teclas digitadas, conteudo privado, prints, audio, webcam ou mensagens pessoais.
