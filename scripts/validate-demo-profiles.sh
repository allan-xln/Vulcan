#!/usr/bin/env bash
set -euo pipefail

API_URL="${API_URL:-http://localhost:3001}"
TENANT_ID="${TENANT_ID:-00000000-0000-0000-0000-000000000301}"

USERS=(
  "teste:teste"
  "diretor:diretor"
  "coordenador:coordenador"
  "gerente:gerente"
  "supervisor:supervisor"
  "lider:lider"
  "operador1:operador1"
  "operador2:operador2"
  "operador3:operador3"
)

json_get() {
  python3 -c "$1"
}

echo "Validando perfis demo em ${API_URL}"
echo "Tenant: ${TENANT_ID}"
echo

for credential in "${USERS[@]}"; do
  username="${credential%%:*}"
  password="${credential##*:}"
  login_payload="{\"username\":\"${username}\",\"password\":\"${password}\"}"

  token="$(
    curl -sS -H "Content-Type: application/json" \
      -d "${login_payload}" \
      "${API_URL}/auth/login" | json_get 'import sys,json; print(json.load(sys.stdin).get("accessToken",""))'
  )"

  if [[ -z "${token}" ]]; then
    echo "ERRO ${username}: login falhou"
    exit 1
  fi

  hierarchy_count="$(
    curl -sS -H "Authorization: Bearer ${token}" -H "X-Tenant-Id: ${TENANT_ID}" \
      "${API_URL}/hierarchy" | json_get 'import sys,json; print(len(json.load(sys.stdin)))'
  )"
  devices_count="$(
    curl -sS -H "Authorization: Bearer ${token}" -H "X-Tenant-Id: ${TENANT_ID}" \
      "${API_URL}/devices" | json_get 'import sys,json; print(len(json.load(sys.stdin)))'
  )"
  total_events="$(
    curl -sS -H "Authorization: Bearer ${token}" -H "X-Tenant-Id: ${TENANT_ID}" \
      "${API_URL}/operational-intelligence" | json_get 'import sys,json; print(json.load(sys.stdin).get("totalEvents",0))'
  )"

  printf "%-12s hierarquia=%-2s dispositivos=%-2s eventos24h=%s\n" "${username}" "${hierarchy_count}" "${devices_count}" "${total_events}"
done

echo
echo "Validacao concluida."
