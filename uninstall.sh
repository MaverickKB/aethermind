#!/usr/bin/env bash
# Uninstall AetherMind Pro Pro-managed files. Preserves project .aethermind/ continuity.
#   sudo aethermind-pro-uninstall   (or)   sudo ./uninstall.sh
set -euo pipefail

PREFIX="${AETHERMIND_PRO_PREFIX:-/opt/aethermind-pro}"
BIN_DIR="${AETHERMIND_PRO_BIN_DIR:-/usr/local/bin}"

echo "AetherMind Pro uninstall: preserving user continuity by default."
rm -f "$BIN_DIR/aethermind-pro" "$BIN_DIR/aethermind-pro-uninstall"
if [ -L "$PREFIX/current" ]; then
  target="$(readlink "$PREFIX/current")"
  rm -f "$PREFIX/current"
  rm -rf "$target"
fi
rm -rf "$PREFIX/releases"
echo "Removed Pro-managed install files. Project .aethermind continuity stores were not touched."
