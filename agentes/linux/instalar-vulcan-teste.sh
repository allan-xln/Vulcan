#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

TENANT_ID="00000000-0000-0000-0000-000000000301"
MEMBERSHIP_ID="00000000-0000-0000-0000-000000300005"
BACKEND_URL="${VULCAN_BACKEND_URL:-http://localhost:3001}"
ENROLLMENT_TOKEN="${VULCAN_ENROLLMENT_TOKEN:-vulcan-local-enrollment-token}"
LINKED_USER="teste"
ROLE_LEVEL="user"
DEPARTMENT="Operacoes"
INSTALL_DEPS="false"
COLLECT_WINDOW_TITLE="false"
COLLECT_BROWSER_DOMAIN="false"
COLLECT_BROWSER_URL="false"
COLLECT_PROCESS_LIST="false"

usage() {
  cat <<USAGE
Vulcan Agent - instalador amigavel do ambiente teste

Uso:
  bash instalar-vulcan-teste.sh [opcoes]

Opcoes:
  --backend-url URL        Backend Vulcan. Padrao: http://localhost:3001
  --install-deps          Instala xdotool via apt quando disponivel.
  --collect-window-title  Coleta titulo da janela ativa quando o sistema permitir.
  --collect-browser-domain Coleta dominio do navegador somente quando a politica permitir.
  --collect-browser-url   Coleta URL sem querystring somente quando a politica permitir.
  --collect-process-list  Usa heuristica limitada de processos quando Wayland bloquear janela ativa.
  -h, --help              Mostra esta ajuda.

Este instalador vincula a maquina ao usuario local de teste:
  Login Vulcan: teste
  Tenant: Vulcan Demo
  Membership: $MEMBERSHIP_ID
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --backend-url) BACKEND_URL="$2"; shift 2 ;;
    --install-deps) INSTALL_DEPS="true"; shift ;;
    --collect-window-title) COLLECT_WINDOW_TITLE="true"; shift ;;
    --collect-browser-domain) COLLECT_BROWSER_DOMAIN="true"; shift ;;
    --collect-browser-url) COLLECT_BROWSER_URL="true"; shift ;;
    --collect-process-list) COLLECT_PROCESS_LIST="true"; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Opcao desconhecida: $1" >&2; usage; exit 2 ;;
  esac
done

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Faltou o comando obrigatorio: $1" >&2
    exit 1
  fi
}

echo "=============================================="
echo " Vulcan Agent - ambiente teste"
echo "=============================================="
echo "Backend:      $BACKEND_URL"
echo "Usuario:      $LINKED_USER"
echo "Departamento: $DEPARTMENT"
echo "Escopo:       uso real deste notebook"
echo
echo "Privacidade: o agente nao coleta senhas, teclas digitadas,"
echo "screenshots, audio, webcam ou clipboard."
echo

require_command python3
require_command systemctl

if [[ ! -f "$SCRIPT_DIR/install.sh" || ! -f "$SCRIPT_DIR/vulcan_agent.py" ]]; then
  echo "Nao encontrei install.sh e vulcan_agent.py em: $SCRIPT_DIR" >&2
  echo "Execute este instalador dentro da pasta do pacote Linux do Vulcan Agent." >&2
  exit 1
fi

if command -v curl >/dev/null 2>&1; then
  if curl -fsS "$BACKEND_URL/agent/status" >/dev/null 2>&1; then
    echo "Backend Vulcan acessivel."
  else
    echo "Aviso: nao consegui validar $BACKEND_URL/agent/status agora."
    echo "A instalacao continua; o agente sincroniza automaticamente quando o backend estiver acessivel."
  fi
fi

INSTALL_ARGS=(
  --tenant-id "$TENANT_ID"
  --backend-url "$BACKEND_URL"
  --enrollment-token "$ENROLLMENT_TOKEN"
  --linked-user "$LINKED_USER"
  --role-level "$ROLE_LEVEL"
  --department "$DEPARTMENT"
  --membership-id "$MEMBERSHIP_ID"
)

if [[ "$INSTALL_DEPS" == "true" ]]; then
  INSTALL_ARGS+=(--install-deps)
fi

if [[ "$COLLECT_WINDOW_TITLE" == "true" ]]; then
  INSTALL_ARGS+=(--collect-window-title)
fi
if [[ "$COLLECT_BROWSER_DOMAIN" == "true" ]]; then
  INSTALL_ARGS+=(--collect-browser-domain)
fi
if [[ "$COLLECT_BROWSER_URL" == "true" ]]; then
  INSTALL_ARGS+=(--collect-browser-url)
fi
if [[ "$COLLECT_PROCESS_LIST" == "true" ]]; then
  INSTALL_ARGS+=(--collect-process-list)
fi

bash "$SCRIPT_DIR/install.sh" "${INSTALL_ARGS[@]}"

AGENT="$HOME/.local/share/vulcan/agent/vulcan_agent.py"
if [[ -x "$AGENT" ]]; then
  echo
  echo "Fazendo primeira vinculacao/sincronizacao..."
  "$AGENT" enroll >/dev/null 2>&1 || true
  "$AGENT" heartbeat >/dev/null 2>&1 || true
  "$AGENT" sync >/dev/null 2>&1 || true
  echo
  "$AGENT" status
fi

echo
echo "Instalacao concluida."
echo "Status: systemctl --user status vulcan-agent.service --no-pager"
echo "Logs:   journalctl --user -u vulcan-agent.service -f"
