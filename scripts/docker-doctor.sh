#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "Usuário atual: $(whoami)"
echo "Grupos atuais: $(id -nG)"
echo

if [ -S /var/run/docker.sock ]; then
  echo "Docker socket:"
  ls -l /var/run/docker.sock
else
  echo "Docker socket não encontrado em /var/run/docker.sock"
fi

echo
echo "Grupo docker:"
getent group docker || echo "grupo docker não existe"

echo
if docker info >/dev/null 2>&1; then
  echo "OK: este usuário consegue falar com o Docker daemon."
  echo
  echo "Próximo comando:"
  echo "  cd $ROOT_DIR && ./scripts/docker-up.sh"
  exit 0
fi

echo "Problema: este usuário NÃO consegue falar com o Docker daemon."
echo
echo "Nesta máquina, o usuário 'allan' aparece no grupo docker."
echo "O usuário atual precisa ser 'allan' ou estar no grupo docker."
echo
echo "Comandos recomendados:"
echo
echo "1. Abrir um terminal como allan e entrar no projeto:"
echo "  cd $ROOT_DIR"
echo
echo "2. Atualizar a sessão de grupos, se necessário:"
echo "  newgrp docker"
echo
echo "3. Subir tudo em Docker:"
echo "  ./scripts/docker-up.sh"
echo
echo "Se ainda falhar, use uma conta sudo/admin para adicionar seu usuário ao grupo docker:"
echo "  sudo usermod -aG docker allan"
echo
echo "Depois faça logout/login ou rode:"
echo "  newgrp docker"
