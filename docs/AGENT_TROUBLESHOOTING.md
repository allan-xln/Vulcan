# Vulcan Agent — troubleshooting

## Coleta inicial

Execute sem copiar segredos para o chamado:

```text
vulcan-agent version
vulcan-agent status
vulcan-agent health
vulcan-agent diagnostics
vulcan-agent policy
vulcan-agent logs --lines 200
vulcan-agent test-connection
```

Registre hostname, agent ID, device ID, versão, revisão de política, profundidade da fila,
relógio local e horário do erro.

## Enrollment falha

- `HTTPS is mandatory`: use certificado válido; no endpoint ERS temporário, HTTP só é
  aceito para IP privado com `--allow-insecure-private-network`; localhost de
  desenvolvimento usa `--allow-insecure-loopback`;
- token expirado/usado/revogado: gere outro token; não aumente vida sem necessidade;
- perfil divergente: o perfil do comando deve ser igual ao perfil fixado no token;
- já enrolled: revogue com `unenroll` antes de gerar outra identidade;
- certificado inválido: corrija cadeia, hostname ou relógio; não desative validação TLS.

## `401` depois do enrollment

Verifique relógio, revogação e integridade dos arquivos locais. Nonces são de uso único;
retry cria request e nonce novos. Se identidade/chave estiver corrompida, preserve
evidências, revogue no servidor e faça re-enrollment aprovado.

## Política rejeitada

Confira assinatura, tenant/agent, revisão, perfil e intervalos. Módulos visuais, keylogger,
microfone, webcam e shell são sempre rejeitados. O agente mantém `policy.previous.json`
para rollback.

## Fila cresce

`status` informa profundidade, bytes cifrados e idade do item mais antigo. Verifique:

1. acesso HTTPS;
2. resposta do gateway e banco;
3. relógio;
4. volume/frequência da política;
5. espaço em disco e permissões;
6. eventos recusados por schema.

Não apague `queue.db` para “corrigir” o sintoma. Ao reconectar, o agente mantém
`occurredAt`, marca replay offline e reduz envio por lotes.

## Atividade indisponível

Em Linux headless ou Wayland sem API suportada, foreground/idle pode ficar `unsupported`.
Em Windows, serviço e sessão são isolados; a coleta multi-sessão definitiva depende do
helper de sessão autenticado ainda não entregue. O agente deve reportar ausência de fonte,
nunca inventar uso.

## Serviço

Linux:

```bash
systemctl --user status vulcan-agent-user
sudo systemctl status vulcan-agent
journalctl --user -u vulcan-agent-user --since today
sudo journalctl -u vulcan-agent --since today
```

Windows:

```powershell
Get-Service VulcanAgent
sc.exe query VulcanAgent
Get-Content "$env:ProgramData\Vulcan\Agent\logs\agent.jsonl" -Tail 200
```

## Pacote

Valide `SHA256SUMS` antes de instalar. MSI sem assinatura Authenticode ou release cujo SBOM
não corresponda ao checksum não deve avançar para produção.
