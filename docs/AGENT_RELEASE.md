# Vulcan Agent — release

## Versão 0.2.0

Artefatos:

- `VulcanAgent.exe`;
- `VulcanAgent-Windows-x64.msi`;
- `vulcan-agent_0.2.0_amd64.deb`;
- `vulcan-agent_0.2.0_sbom.cdx.json`;
- `SHA256SUMS`.

`dist/` e os downloads copiados ao frontend são gerados e ignorados pelo Git.

## Build

Requisitos: Go compatível com o `go.mod`, `dpkg-deb` e WiX 3 em Windows ou
`wixl` + `msibuild` em Linux.

```bash
cd agentes/agent
VERSION=0.2.0 ./build-release.sh
```

Em um ambiente com ferramentas extraídas:

```bash
LD_LIBRARY_PATH=/caminho/msitools/usr/lib/x86_64-linux-gnu \
WIXL_BINARY=/caminho/msitools/usr/bin/wixl \
MSIBUILD_BINARY=/caminho/msitools/usr/bin/msibuild \
WIXL_WXIDIR=/caminho/msitools/usr/share/wixl/include \
VERSION=0.2.0 ./build-release.sh
```

O fallback Linux ajusta explicitamente no banco MSI:

- `SecureCustomProperties`;
- `MsiHiddenProperties`;
- `HideTarget` das ações que transportam o token.

Isso deve ser validado a cada alteração do WXS.

## Validação obrigatória

```bash
corepack pnpm verify:agent
sha256sum --check dist/SHA256SUMS
dpkg-deb --info dist/vulcan-agent_0.2.0_amd64.deb
```

Além da inspeção do pacote, execute:

- enrollment contra API real de homologação;
- aplicação de política assinada;
- envio e idempotência;
- queda de API, fila, retorno e replay;
- consumo em repouso;
- instalação/upgrade/reparo/remoção em VM Windows;
- instalação/upgrade/remoção em VM Debian/Ubuntu;
- assinatura Authenticode e validação da assinatura;
- piloto por anéis.

Validação observada em 2026-07-23 para o release local `0.2.0`:

- `corepack pnpm verify:agent`: passou com validação SQL, race, vet, cross-test/vet Windows
  e cinco testes de contrato da API v2;
- suítes Python completas: 58 testes passaram;
- frontend: lint, typecheck, cinco unitários, E2E Chromium e build otimizado passaram;
- `SHA256SUMS`, estrutura do `.deb` e tabelas/propriedades sensíveis do MSI foram
  inspecionados;
- `VulcanAgent.exe version` executou pelo Wine;
- o binário Linux real completou enrollment, política, fila offline e replay no protocolo
  v2 local.

Isso não equivale a homologação do MSI/SCM em Windows real nem à instalação do `.deb` sobre
o agente legado ativo. Esses dois testes continuam obrigatórios antes da promoção para
produção.

## Simulador de carga

O simulador cria identidades e eventos reais no protocolo, sempre marcados
`dataOrigin=simulated`. Ele aceita somente 10, 100 ou 1.000 agentes, exige confirmação e
bloqueia ambiente não-loopback sem uma segunda autorização explícita.

```bash
VULCAN_ADMIN_TOKEN='TOKEN_ADMIN_DE_TESTE' go run ./cmd/vulcan-agent-simulator \
  --server http://127.0.0.1:3001 \
  --tenant 00000000-0000-0000-0000-000000000301 \
  --agents 10 \
  --confirm-simulated-data
```

Use apenas em tenant de desenvolvimento: os dispositivos, identidades, auditoria e eventos
simulados são persistentes e intencionalmente visíveis.

## SBOM e licenças

O build gera CycloneDX 1.5 a partir do build info Go. Dependências diretas/transitivas
devem passar por revisão de vulnerabilidades e licenças antes do release. A presença no
SBOM não substitui a política de licenciamento.

## Assinatura e update

Checksum já é obrigatório na entrega. Code signing Windows, assinatura do pacote Linux e
manifesto de update Ed25519 ainda precisam de chaves de produção, cofre, rotação e
cerimônia de release. Auto-update permanece desligado até essa homologação.

## Rollback

Preserve o release anterior assinado e seu SBOM. O MSI usa `MajorUpgrade` e bloqueia
downgrade automático. Um rollback exige mudança aprovada, revogação apenas quando a
identidade será substituída e verificação da fila antes/depois.
