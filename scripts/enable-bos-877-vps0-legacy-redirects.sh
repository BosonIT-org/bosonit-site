#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  ./scripts/enable-bos-877-vps0-legacy-redirects.sh [options]

Options:
  --host HOST          vps0 SSH host. Defaults to $VPS0_HOST or 72.60.28.34
  --user USER          vps0 SSH user. Defaults to $VPS0_USER or kj
  --skip-live-verify   Do not run ./scripts/verify-bos-121-canonical-live.sh after patching
  --print-remote       Print the remote patch script instead of executing it
  -h, --help           Show help
EOF
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

vps0_host="${VPS0_HOST:-72.60.28.34}"
vps0_user="${VPS0_USER:-kj}"
skip_live_verify=0
print_remote=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --host)
      vps0_host="${2:-}"
      shift 2
      ;;
    --user)
      vps0_user="${2:-}"
      shift 2
      ;;
    --skip-live-verify)
      skip_live_verify=1
      shift
      ;;
    --print-remote)
      print_remote=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

for required in ssh python3 grep mktemp; do
  if ! command -v "${required}" >/dev/null 2>&1; then
    echo "Missing required command: ${required}" >&2
    exit 1
  fi
done

read -r -d '' remote_script <<'EOF' || true
set -euo pipefail

target_root="/var/www/bosonit"
htaccess="${target_root}/.htaccess"
anchor="# Serve real files and directories first."
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
rollback_dir="${target_root}/.rollback/BOS-877-${timestamp}"
tmp_file="$(mktemp)"

if [[ ! -f "${htaccess}" ]]; then
  echo "missing_target:${htaccess}" >&2
  exit 1
fi

sudo install -d -m 755 "${rollback_dir}"
sudo cp "${htaccess}" "${rollback_dir}/.htaccess.before"
sudo cp "${htaccess}" "${tmp_file}"

python3 - "${tmp_file}" "${anchor}" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
anchor = sys.argv[2]
text = path.read_text()
rules = [
    "RewriteRule ^utility-sites/mortgage-payment-calculator/?$ /mortgage-calculator/ [R=301,L]",
    "RewriteRule ^utility-sites/mortgage-payment-calculator/index\\.html$ /mortgage-calculator/ [R=301,L]",
    "RewriteRule ^utility-sites/calorie-deficit-calculator/?$ /calorie-calculator/ [R=301,L]",
    "RewriteRule ^utility-sites/calorie-deficit-calculator/index\\.html$ /calorie-calculator/ [R=301,L]",
    "RewriteRule ^utility-sites/sales-tax-calculator/?$ /sales-tax-calculator/ [R=301,L]",
    "RewriteRule ^utility-sites/sales-tax-calculator/index\\.html$ /sales-tax-calculator/ [R=301,L]",
]

missing = [rule for rule in rules if rule not in text]
if not missing:
    path.write_text(text)
    print("RESULT=noop")
    raise SystemExit(0)

block = (
    "# BOS-121 canonical calculator aliases.\n"
    + "\n".join(rules)
    + "\n"
)

if anchor not in text:
    raise SystemExit(f"anchor_not_found:{anchor}")

text = text.replace(anchor, block + "\n" + anchor, 1)
path.write_text(text)
print("RESULT=patched")
PY

sudo install -m 644 "${tmp_file}" "${htaccess}"
rm -f "${tmp_file}"

grep -Fq 'RewriteRule ^utility-sites/mortgage-payment-calculator/?$ /mortgage-calculator/ [R=301,L]' "${htaccess}"
grep -Fq 'RewriteRule ^utility-sites/calorie-deficit-calculator/?$ /calorie-calculator/ [R=301,L]' "${htaccess}"
grep -Fq 'RewriteRule ^utility-sites/sales-tax-calculator/?$ /sales-tax-calculator/ [R=301,L]' "${htaccess}"

echo "ROLLBACK_SNAPSHOT=${rollback_dir}/.htaccess.before"
echo "ROLLBACK_COMMAND=sudo cp ${rollback_dir}/.htaccess.before ${htaccess}"
EOF

if [[ "${print_remote}" -eq 1 ]]; then
  printf '%s\n' "${remote_script}"
  exit 0
fi

ssh_target="${vps0_user}@${vps0_host}"
echo "Patching BOS-877 legacy redirects on ${ssh_target}:${vps0_host}"
remote_output="$(
  ssh -o StrictHostKeyChecking=accept-new "${ssh_target}" "bash -s" <<<"${remote_script}"
)"
printf '%s\n' "${remote_output}"

if [[ "${skip_live_verify}" -eq 1 ]]; then
  exit 0
fi

echo "Running BOS-121 live verification after remote patch..."
(
  cd "${REPO_ROOT}"
  ./scripts/verify-bos-121-canonical-live.sh
)
