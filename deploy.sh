#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   ./deploy.sh --target vps0
#   STACK_USER=bosonit.org ./deploy.sh --target stackcp
#   STACK_USER=bosonit.org ./deploy.sh --target both
TARGET_MODE="vps0"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --target)
      TARGET_MODE="${2:-}"
      shift 2
      ;;
    *)
      echo "Unknown option: $1" >&2
      exit 2
      ;;
  esac
done

if [[ "$TARGET_MODE" != "vps0" && "$TARGET_MODE" != "stackcp" && "$TARGET_MODE" != "both" ]]; then
  echo "Invalid --target value: $TARGET_MODE (expected vps0|stackcp|both)" >&2
  exit 2
fi

VPS0_HOST="${VPS0_HOST:-72.60.28.34}"
VPS0_USER="${VPS0_USER:-kj}"
STACK_USER="${STACK_USER:-}"

echo "🔄  Building site locally…"
npm ci
npm run build

if [[ "$TARGET_MODE" == "vps0" || "$TARGET_MODE" == "both" ]]; then
  echo "🚀  Deploying to vps0 origin (${VPS0_USER}@${VPS0_HOST}:/var/www/bosonit)"
  ssh "${VPS0_USER}@${VPS0_HOST}" "sudo mkdir -p /var/www/bosonit"
  rsync -avz \
    --rsync-path="sudo rsync" \
    --chmod=Du=rwx,Dg=rx,Do=rx,Fu=rw,Fg=r,Fo=r \
    dist/ "${VPS0_USER}@${VPS0_HOST}:/var/www/bosonit/"
fi

if [[ "$TARGET_MODE" == "stackcp" || "$TARGET_MODE" == "both" ]]; then
  if [[ -z "$STACK_USER" ]]; then
    echo "STACK_USER is required for stackcp deploy target." >&2
    exit 2
  fi
  echo "🚀  Mirroring to StackCP (${STACK_USER}@ssh.us.stackcp.com:~/public_html/bosonit.org)"
  rsync -avz --delete \
    --chmod=Du=rwx,Dg=rx,Do=rx,Fu=rw,Fg=r,Fo=r \
    dist/ "${STACK_USER}@ssh.us.stackcp.com:~/public_html/bosonit.org/"
fi

echo "✅  Deploy complete (${TARGET_MODE})."
