# Vulcan Agent — políticas

## Princípios

O servidor governa módulos, frequência, privacidade, fila e comandos. O agente aceita apenas
um envelope `v1` Ed25519 assinado para seu tenant, identidade e perfil.

Precedência atual:

1. dispositivo;
2. site;
3. tenant;
4. defaults seguros.

Departamento está modelado para token e política, mas a resolução efetiva nesta entrega
considera dispositivo, site e tenant. A UI mostra revisão e escopo; a exibição campo a
campo da origem ainda é trabalho restante.

## Defaults

Todos os perfis coletam self-health, inventário, métricas do sistema e rede passiva.
Workstation habilita atividade sem título. Server habilita checks configurados. Collector
habilita discovery, mas um allowlist vazio produz zero alvos.

```json
{
  "schemaVersion": "v1",
  "profile": "workstation",
  "modules": {
    "activity": {
      "enabled": true,
      "windowTitles": false,
      "privacyFilters": ["password", "senha", "auth", "bank", "banco"]
    },
    "printing": {"enabled": false, "documentNames": false},
    "visual": {"screenCapture": false, "liveSupport": false}
  },
  "privacy": {
    "collectTypedContent": false,
    "collectClipboard": false,
    "collectCredentials": false
  }
}
```

## Intervalos e fila

Intervalos válidos ficam entre 5 segundos e 7 dias. Defaults: health/métricas 60 s, rede
300 s, inventário 6 h e sync 30 s. A fila padrão limita 10.000 eventos, 100 MiB, lote 100
e retenção declarada de 168 h.

Quando cheia, a fila remove primeiro dados antigos de menor prioridade. Crítico e auditoria
não são sacrificados enquanto houver eventos menos prioritários; se só restarem itens
protegidos, o enqueue falha de forma explícita.

`retentionHours` remove durante o enqueue somente eventos locais expirados de prioridade
inferior a crítico/auditoria. Limites aceitos: 100–1.000.000 eventos, 1 MiB–10 GiB,
retenção de 1–720 horas e lotes de 1–500.

## Perfis

- Workstation: atividade, sessão, saúde, rede e inventário;
- Server: sem produtividade; métricas e probes HTTP/TCP;
- Collector: sem produtividade; discovery somente leitura em alvos explícitos.

Uma política de perfil incompatível é rejeitada e a última política válida é preservada.

## Módulos não disponíveis

Printing completo, Windows Event Log, USB, inventário detalhado de software, containers,
SNMP/traps/flows e auto-update ainda não possuem collector final. A UI não deve marcá-los
como operacionais. Nenhuma política habilita módulos visuais ou execução arbitrária.

## Mudança segura

Crie uma nova revisão, aplique primeiro a um dispositivo/site piloto e confira
`policyStatus=applied`, saúde dos collectors e volume da fila. Uma política inválida não é
ativada e gera estado auditável.
