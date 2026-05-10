#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  ./scripts/enable-bos-877-vps0-legacy-redirects.sh [options]

Options:
  --host HOST          vps0 SSH host. Defaults to $VPS0_HOST or 72.60.28.34
  --user USER          vps0 SSH user. Defaults to $VPS0_USER or kj
  --skip-live-verify   Do not run BOS-121 public redirect verification after patching
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

origin_conf="/opt/bmos-infra/nginx/default.conf"
site_container="bmos-site-prod-1"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
rollback_dir="$(dirname "${origin_conf}")/.rollback/BOS-877-${timestamp}"
tmp_file="$(mktemp)"

if [[ ! -f "${origin_conf}" ]]; then
  echo "missing_target:${origin_conf}" >&2
  exit 1
fi

for required in docker python3 stat; do
  if ! command -v "${required}" >/dev/null 2>&1; then
    echo "missing_remote_command:${required}" >&2
    exit 1
  fi
done

owner="$(stat -c %U "${origin_conf}")"
group="$(stat -c %G "${origin_conf}")"

sudo -n install -d -m 755 "${rollback_dir}"
sudo -n cp "${origin_conf}" "${rollback_dir}/default.conf.before"
sudo -n cp "${origin_conf}" "${tmp_file}"
sudo -n chown "$(id -un):$(id -gn)" "${tmp_file}"

python3 - "${tmp_file}" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
text = path.read_text()
original = text
start = "  # BOS-121 canonical calculator aliases.\n"
end = "  # End BOS-121 canonical calculator aliases.\n"
rules = {
    "mortgage-payment-calculator": "mortgage-calculator",
    "calorie-deficit-calculator": "calorie-calculator",
    "sales-tax-calculator": "sales-tax-calculator",
}

lines = [start.rstrip("\n")]
for legacy, canonical in rules.items():
    for suffix in ("", "/", "/index.html"):
        lines.extend([
            f"  location = /utility-sites/{legacy}{suffix} {{",
            f"    return 301 /{canonical}/;",
            "  }",
        ])
lines.append(end.rstrip("\n"))
block = "\n".join(lines) + "\n"

if start in text and end in text:
    before, rest = text.split(start, 1)
    _, after = rest.split(end, 1)
    text = before + block + after
else:
    anchor = "  location ~* \\.(?:css|js|mjs|json|png|jpe?g|gif|svg|webp|ico|woff2?|ttf)$ {\n"
    if anchor not in text:
        raise SystemExit(f"anchor_not_found:{anchor.strip()}")
    text = text.replace(anchor, block + anchor, 1)

path.write_text(text)
print("RESULT=noop" if text == original else "RESULT=patched")
PY

sudo -n install -o "${owner}" -g "${group}" -m 644 "${tmp_file}" "${origin_conf}"
rm -f "${tmp_file}"

sudo -n docker exec "${site_container}" nginx -t
sudo -n docker exec "${site_container}" nginx -s reload

grep -Fq 'location = /utility-sites/mortgage-payment-calculator/' "${origin_conf}"
grep -Fq 'location = /utility-sites/calorie-deficit-calculator/' "${origin_conf}"
grep -Fq 'location = /utility-sites/sales-tax-calculator/' "${origin_conf}"

echo "ROLLBACK_SNAPSHOT=${rollback_dir}/default.conf.before"
echo "ROLLBACK_COMMAND=sudo cp ${rollback_dir}/default.conf.before ${origin_conf} && sudo docker exec ${site_container} nginx -t && sudo docker exec ${site_container} nginx -s reload"
EOF

if [[ "${print_remote}" -eq 1 ]]; then
  printf '%s\n' "${remote_script}"
  exit 0
fi

ssh_target="${vps0_user}@${vps0_host}"
echo "Patching BOS-877 legacy redirects on ${ssh_target}:${vps0_host}"
remote_output="$(
  ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new "${ssh_target}" "bash -s" <<<"${remote_script}"
)"
printf '%s\n' "${remote_output}"

if [[ "${skip_live_verify}" -eq 1 ]]; then
  exit 0
fi

echo "Running BOS-121 live verification after remote patch..."
if [[ -x "${REPO_ROOT}/scripts/verify-bos-121-canonical-live.sh" ]]; then
  (
    cd "${REPO_ROOT}"
    ./scripts/verify-bos-121-canonical-live.sh
  )
  exit 0
fi

if ! command -v curl >/dev/null 2>&1; then
  echo "Missing required command for live verification: curl" >&2
  exit 1
fi

nonce="$(date +%s)-$RANDOM"
for legacy in mortgage-payment-calculator calorie-deficit-calculator sales-tax-calculator; do
  case "${legacy}" in
    mortgage-payment-calculator)
      canonical="mortgage-calculator"
      ;;
    calorie-deficit-calculator)
      canonical="calorie-calculator"
      ;;
    sales-tax-calculator)
      canonical="sales-tax-calculator"
      ;;
    *)
      echo "Unknown legacy calculator slug: ${legacy}" >&2
      exit 1
      ;;
  esac
  for suffix in "" "/" "/index.html"; do
    headers="$(mktemp)"
    body="$(mktemp)"
    url="https://www.bosonit.org/utility-sites/${legacy}${suffix}?verify=${nonce}"
    status="$(curl -sS -D "${headers}" -o "${body}" -w '%{http_code}' "${url}" || true)"
    rm -f "${body}"
    if [[ "${status}" != "301" ]]; then
      cat "${headers}" >&2 || true
      rm -f "${headers}"
      echo "Expected 301 for ${url}, got ${status:-000}." >&2
      exit 1
    fi
    if ! grep -Eiq "location: (https://www\\.bosonit\\.org)?/${canonical}/" "${headers}"; then
      cat "${headers}" >&2 || true
      rm -f "${headers}"
      echo "Expected redirect location to /${canonical}/ for ${url}." >&2
      exit 1
    fi
    rm -f "${headers}"
  done
done

for canonical in mortgage-calculator calorie-calculator sales-tax-calculator; do
  body="$(mktemp)"
  status="$(curl -sS -o "${body}" -w '%{http_code}' "https://www.bosonit.org/${canonical}/?verify=${nonce}" || true)"
  if [[ "${status}" != "200" ]]; then
    rm -f "${body}"
    echo "Expected 200 for /${canonical}/, got ${status:-000}." >&2
    exit 1
  fi
  if ! grep -Fq "https://www.bosonit.org/${canonical}/" "${body}"; then
    rm -f "${body}"
    echo "Canonical body for /${canonical}/ does not include its self URL." >&2
    exit 1
  fi
  rm -f "${body}"
done

echo "BOS-121 live verification passed."
