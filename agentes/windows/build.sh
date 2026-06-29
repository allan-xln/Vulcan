#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
GO_BIN="${ROOT_DIR}/.tools/go/bin/go"

if [[ ! -x "${GO_BIN}" ]]; then
  GO_BIN="$(command -v go || true)"
fi

if [[ -z "${GO_BIN}" ]]; then
  echo "Go was not found. Install Go 1.25+ or keep the portable toolchain at .tools/go." >&2
  exit 1
fi

OUT_DIR="${ROOT_DIR}/agentes/installers/windows"
mkdir -p "${OUT_DIR}"

cd "${ROOT_DIR}/agentes/windows/agent"
GOOS=windows GOARCH=amd64 CGO_ENABLED=0 "${GO_BIN}" mod tidy
GOOS=windows GOARCH=amd64 CGO_ENABLED=0 "${GO_BIN}" build -buildvcs=false -trimpath -ldflags="-s -w -H=windowsgui" -o "${OUT_DIR}/VulcanAgent.exe" ./cmd/vulcan-agent
GOOS=windows GOARCH=amd64 CGO_ENABLED=0 "${GO_BIN}" build -buildvcs=false -trimpath -ldflags="-s -w" -o "${OUT_DIR}/VulcanAgentSetup.exe" ./cmd/vulcan-agent

cd "${ROOT_DIR}"
cp agentes/windows/scripts/*.ps1 "${OUT_DIR}/"
cp agentes/windows/scripts/install-gpo.cmd "${OUT_DIR}/"
cp agentes/windows/README.md "${OUT_DIR}/README-Windows-Agent.md"

cd "${OUT_DIR}"
zip -q -r VulcanAgent-Windows-x64.zip VulcanAgent.exe VulcanAgentSetup.exe *.ps1 install-gpo.cmd README-Windows-Agent.md
echo "Built ${OUT_DIR}/VulcanAgentSetup.exe"
echo "Built ${OUT_DIR}/VulcanAgent-Windows-x64.zip"
