#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
OUT_DIR="$ROOT_DIR/agentes/installers/linux"
mkdir -p "$OUT_DIR"

cp "$ROOT_DIR/agentes/linux/vulcan_agent.py" "$OUT_DIR/"
cp "$ROOT_DIR/agentes/linux/install.sh" "$OUT_DIR/"
cp "$ROOT_DIR/agentes/linux/instalar-vulcan-teste.sh" "$OUT_DIR/"
cp "$ROOT_DIR/agentes/linux/uninstall.sh" "$OUT_DIR/"
cp "$ROOT_DIR/agentes/linux/status.sh" "$OUT_DIR/"
cp "$ROOT_DIR/agentes/linux/README.md" "$OUT_DIR/README-Linux-Agent.md"
chmod +x "$OUT_DIR"/*.sh "$OUT_DIR/vulcan_agent.py"

cd "$OUT_DIR"
zip -q -r VulcanAgent-Linux.zip vulcan_agent.py install.sh instalar-vulcan-teste.sh uninstall.sh status.sh README-Linux-Agent.md
echo "Built $OUT_DIR/VulcanAgent-Linux.zip"
