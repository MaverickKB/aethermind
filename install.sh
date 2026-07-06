#!/usr/bin/env bash
# Git-style install for AetherMind Pro.
#
# Run from a checkout:
#   git clone <remote> aethermind-pro && cd aethermind-pro && sudo ./install.sh
#
# Installs product commands (`aethermind-pro`, `aethermind-pro-uninstall`) from this
# checkout's src/ into a prefix and puts them on PATH. No PYTHONPATH or source layout
# knowledge is required to use the product afterward. Overridable with env:
#   AETHERMIND_PRO_PREFIX   (default /opt/aethermind-pro)
#   AETHERMIND_PRO_BIN_DIR  (default /usr/local/bin)
set -euo pipefail

SELF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PREFIX="${AETHERMIND_PRO_PREFIX:-/opt/aethermind-pro}"
BIN_DIR="${AETHERMIND_PRO_BIN_DIR:-/usr/local/bin}"

if ! command -v python3 >/dev/null 2>&1; then
  echo "error: python3 is required and was not found on PATH" >&2
  exit 1
fi

# Everything below is logged for support; the summary prints the location.
mkdir -p "$PREFIX/logs"
chmod 755 "$PREFIX" "$PREFIX/logs" 2>/dev/null || true
LOG_FILE="$PREFIX/logs/install-$(date -u +%Y%m%d-%H%M%S).log"
touch "$LOG_FILE" && chmod 644 "$LOG_FILE"
exec > >(tee -a "$LOG_FILE") 2>&1
if [ ! -d "$SELF_DIR/src/aethermind_pro" ]; then
  echo "error: $SELF_DIR/src/aethermind_pro not found; run this from an AetherMind Pro checkout" >&2
  exit 1
fi

# safe.directory keeps `sudo ./install.sh` (root running git in a user-owned
# checkout) from failing the "dubious ownership" check and silently falling back.
if command -v git >/dev/null 2>&1 && git -c safe.directory="$SELF_DIR" -C "$SELF_DIR" rev-parse --short=12 HEAD >/dev/null 2>&1; then
  VERSION="$(git -c safe.directory="$SELF_DIR" -C "$SELF_DIR" rev-parse --short=12 HEAD)"
else
  VERSION="$(date -u +%Y%m%d%H%M%S)"
fi

INSTALL_DIR="$PREFIX/releases/$VERSION"
mkdir -p "$PREFIX/releases" "$BIN_DIR"
rm -rf "$INSTALL_DIR"
mkdir -p "$INSTALL_DIR"
cp -R "$SELF_DIR/src" "$INSTALL_DIR/src"
if [ -f "$SELF_DIR/pyproject.toml" ]; then
  cp "$SELF_DIR/pyproject.toml" "$INSTALL_DIR/pyproject.toml"
fi
cp "$SELF_DIR/uninstall.sh" "$INSTALL_DIR/uninstall.sh"
ln -sfn "$INSTALL_DIR" "$PREFIX/current"

# Installed files must be usable by the (often non-root) user who runs the
# product, regardless of the installing shell's umask. Force readable/traversable.
chmod 755 "$PREFIX" "$PREFIX/releases" "$INSTALL_DIR"
find "$INSTALL_DIR" -type d -exec chmod 755 {} +
find "$INSTALL_DIR" -type f -exec chmod 644 {} +

# Replace any existing bin entries outright (they may be stale symlinks from a
# prior install; writing through a symlink would clobber its target instead).
rm -f "$BIN_DIR/aethermind-pro" "$BIN_DIR/aethermind-pro-uninstall"
cat > "$BIN_DIR/aethermind-pro" <<WRAPPER
#!/usr/bin/env bash
set -euo pipefail
INSTALL_ROOT="\${AETHERMIND_PRO_INSTALL_ROOT:-$INSTALL_DIR}"
export PYTHONPATH="\$INSTALL_ROOT/src\${PYTHONPATH:+:\$PYTHONPATH}"
exec python3 -m aethermind_pro.cli "\$@"
WRAPPER

cat > "$BIN_DIR/aethermind-pro-uninstall" <<UNINSTALLER
#!/usr/bin/env bash
set -euo pipefail
AETHERMIND_PRO_PREFIX="\${AETHERMIND_PRO_PREFIX:-$PREFIX}" AETHERMIND_PRO_BIN_DIR="\${AETHERMIND_PRO_BIN_DIR:-$BIN_DIR}" bash "$INSTALL_DIR/uninstall.sh"
UNINSTALLER
chmod 755 "$BIN_DIR/aethermind-pro" "$BIN_DIR/aethermind-pro-uninstall"

# Harness integration at install time. Surfaces are per-user, so integration
# runs as the invoking user (SUDO_USER under sudo), never as root state.
# Consent stays default-deny: interactive prompt defaults to No; non-interactive
# installs integrate only with AETHERMIND_PRO_INTEGRATE_HARNESSES=yes.
TARGET_USER="${SUDO_USER:-$(id -un)}"
run_as_target() {
  if [ "$TARGET_USER" = "$(id -un)" ]; then
    "$@"
  else
    sudo -u "$TARGET_USER" -H "$@"
  fi
}
# Only first-class harnesses get the integration offer; unknown candidates
# require trust review and must not be reported as integrated.
discover_detected() {
  run_as_target "$BIN_DIR/aethermind-pro" harnesses discover --json 2>/dev/null \
    | python3 -c 'import json,sys; d=json.load(sys.stdin); print(" ".join(h["name"] for h in d.get("harnesses",[]) if h.get("detected") and h.get("classification")=="first_class_known"))' 2>/dev/null \
    || true
}
discover_review_needed() {
  run_as_target "$BIN_DIR/aethermind-pro" harnesses discover --json 2>/dev/null \
    | python3 -c 'import json,sys; d=json.load(sys.stdin); print(" ".join(h["name"] for h in d.get("harnesses",[]) if h.get("detected") and h.get("classification")!="first_class_known"))' 2>/dev/null \
    || true
}
# Discovery is read-only and always runs so the closing summary is truthful;
# writing into a harness stays consent-gated below.
INTEGRATE="${AETHERMIND_PRO_INTEGRATE_HARNESSES:-ask}"
DETECTED="$(discover_detected)"
REVIEW_NEEDED="$(discover_review_needed)"
INTEGRATED=""
INTEGRATION_FAILED=""
if [ "$INTEGRATE" = "ask" ] && [ -t 0 ]; then
  if [ -n "$DETECTED" ]; then
    printf 'Detected agent harnesses for user %s: %s\n' "$TARGET_USER" "$DETECTED"
    printf 'Integrate AetherMind Pro into these harnesses now? [y/N] '
    REPLY=""
    read -r REPLY || REPLY=""
    case "$REPLY" in
      y|Y|yes|YES) INTEGRATE=yes ;;
      *) INTEGRATE=no ;;
    esac
  fi
fi
if [ "$INTEGRATE" = "yes" ] && [ -n "$DETECTED" ]; then
  for HARNESS in $DETECTED; do
    if run_as_target "$BIN_DIR/aethermind-pro" harnesses bootstrap apply --name "$HARNESS" --approve --json >/dev/null 2>&1; then
      INTEGRATED="$INTEGRATED $HARNESS"
    else
      INTEGRATION_FAILED="$INTEGRATION_FAILED $HARNESS"
    fi
  done
fi
INTEGRATED="${INTEGRATED# }"
INTEGRATION_FAILED="${INTEGRATION_FAILED# }"

# Help files live with the release so customers always have offline answers.
HELP_DIR="$INSTALL_DIR/help"
mkdir -p "$HELP_DIR"
if [ -f "$SELF_DIR/README.md" ]; then
  cp "$SELF_DIR/README.md" "$HELP_DIR/README.md"
fi
cat > "$HELP_DIR/QUICKSTART.txt" <<'QUICKSTART'
AetherMind - Quickstart

First value (local-first; no account, no network):
  aethermind-pro first-run --project-root <your project>

Health and orientation:
  aethermind-pro doctor  --project-root <your project>
  aethermind-pro status  --project-root <your project>

Agent harness integration (consent required, run as your normal user):
  aethermind-pro harnesses discover
  aethermind-pro harnesses bootstrap apply --name <harness> --approve
  aethermind-pro harnesses bootstrap remove --all     # rollback

Support and data:
  aethermind-pro support-bundle --output <file.json>  # sanitized support snapshot
  aethermind-pro export        --output <file.json>   # your data, yours to keep

Uninstall (project continuity stores are always preserved):
  aethermind-pro-uninstall
QUICKSTART
cat > "$HELP_DIR/SUPPORT.txt" <<'SUPPORT'
AetherMind - Support

Project home:  https://github.com/MaverickKB/aethermind
(Report issues on GitHub; the canonical diagnostic path is the CLI below.)

If something is wrong:
  1. aethermind-pro doctor --project-root <your project>
  2. aethermind-pro support-bundle --output support.json
  3. Attach support.json to a GitHub issue. It is sanitized: no project
     content, no secrets, no raw paths beyond what you can read yourself.

Install logs are kept under the install prefix in logs/.
Your project continuity lives in <project>/.aethermind/ and is never uploaded.
SUPPORT
find "$HELP_DIR" -type f -exec chmod 644 {} +

# Closing summary: what was found, what was done, where everything lives.
HARNESS_LINE="none detected"
if [ -n "$INTEGRATED" ]; then
  HARNESS_LINE="integrated: $INTEGRATED"
elif [ -n "$DETECTED" ]; then
  HARNESS_LINE="detected (not integrated): $DETECTED"
fi
if [ -n "$REVIEW_NEEDED" ]; then
  HARNESS_LINE="$HARNESS_LINE  [needs trust review: $REVIEW_NEEDED]"
fi
cat <<'BANNER'

   _       _   _            __  __ _         _   ___
  /_\  ___| |_| |_  ___ _ _|  \/  (_)_ _  __| | | _ \_ _ ___
 / _ \/ -_)  _| ' \/ -_) '_| |\/| | | ' \/ _` | |  _/ '_/ _ \
/_/ \_\___|\__|_||_\___|_| |_|  |_|_|_||_\__,_| |_| |_| \___/

BANNER
cat <<SUMMARY
  Install complete.

  Version installed   $VERSION
  Product command     $BIN_DIR/aethermind-pro
  Install directory   $INSTALL_DIR
  Agent harnesses     $HARNESS_LINE
  Install log         $LOG_FILE
  Help files          $HELP_DIR
                      (QUICKSTART.txt, SUPPORT.txt$([ -f "$HELP_DIR/GETTING_STARTED.md" ] && echo ", GETTING_STARTED.md"))

  Start here:
    aethermind-pro first-run --project-root <your project>
    aethermind-pro doctor    --project-root <your project>

  Integrate with an agent harness later (nothing is written without --approve):
    aethermind-pro harnesses discover
    aethermind-pro harnesses bootstrap apply --name <harness> --approve

  Project home: https://github.com/MaverickKB/aethermind
  Uninstall:    aethermind-pro-uninstall  (project continuity is preserved)

SUMMARY
if [ -n "$INTEGRATION_FAILED" ]; then
  echo "  NOTE: integration failed for:$INTEGRATION_FAILED"
  echo "  Run manually as your normal user:"
  echo "    aethermind-pro harnesses bootstrap apply --name <harness> --approve"
  echo ""
fi
