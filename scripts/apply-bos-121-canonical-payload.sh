#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  bash ./scripts/apply-bos-121-canonical-payload.sh [options]

Options:
  --dist-root PATH   Dist root to overlay. Defaults to ./dist
  --base-url URL     Deprecated compatibility flag. Ignored.
  -h, --help         Show help.
EOF
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

dist_root="${REPO_ROOT}/dist"
payload_archive_b64="${BOS_121_CANONICAL_PAYLOAD_B64:-${SCRIPT_DIR}/bos-121-canonical-overlay.tar.gz.base64}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dist-root)
      dist_root="${2:-}"
      shift 2
      ;;
    --base-url)
      shift 2
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

for required in base64 tar mkdir mktemp cp grep; do
  if ! command -v "${required}" >/dev/null 2>&1; then
    echo "Missing required command: ${required}" >&2
    exit 1
  fi
done

if [[ ! -f "${payload_archive_b64}" ]]; then
  echo "Missing payload archive: ${payload_archive_b64}" >&2
  exit 1
fi

temp_dir="$(mktemp -d)"
cleanup() {
  rm -rf "${temp_dir}"
}
trap cleanup EXIT

mkdir -p \
  "${dist_root}" \
  "${dist_root}/utility-sites" \
  "${dist_root}/observatory"

base64 -d "${payload_archive_b64}" > "${temp_dir}/payload.tar.gz"
tar -xzf "${temp_dir}/payload.tar.gz" -C "${temp_dir}"

if [[ ! -d "${temp_dir}/payload" ]]; then
  echo "Decoded payload is missing the expected payload/ root." >&2
  exit 1
fi

cp -R "${temp_dir}/payload/." "${dist_root}/"

declare -A CANONICAL_ALIAS_BY_SLUG=(
  [mortgage-payment-calculator]=mortgage-calculator
  [calorie-deficit-calculator]=calorie-calculator
  [sales-tax-calculator]=sales-tax-calculator
)

grep -Fq 'RewriteRule ^utility-sites/mortgage-payment-calculator/?$ /mortgage-calculator/ [R=301,L]' "${dist_root}/.htaccess"
grep -Fq 'RewriteRule ^utility-sites/calorie-deficit-calculator/?$ /calorie-calculator/ [R=301,L]' "${dist_root}/.htaccess"
grep -Fq 'RewriteRule ^utility-sites/sales-tax-calculator/?$ /sales-tax-calculator/ [R=301,L]' "${dist_root}/.htaccess"

grep -Fq 'href="/mortgage-calculator/"' "${dist_root}/utility-sites/index.html"
grep -Fq 'href="/calorie-calculator/"' "${dist_root}/utility-sites/index.html"
grep -Fq 'href="/sales-tax-calculator/"' "${dist_root}/utility-sites/index.html"

grep -Fq '"preview_url": "/mortgage-calculator/"' "${dist_root}/observatory/utility-sites.latest.json"
grep -Fq '"preview_url": "/calorie-calculator/"' "${dist_root}/observatory/utility-sites.latest.json"
grep -Fq '"preview_url": "/sales-tax-calculator/"' "${dist_root}/observatory/utility-sites.latest.json"

grep -Fq 'https://www.bosonit.org/utility-sites/' "${dist_root}/sitemap.xml"
grep -Fq 'https://www.bosonit.org/mortgage-calculator/' "${dist_root}/sitemap.xml"
grep -Fq 'https://www.bosonit.org/calorie-calculator/' "${dist_root}/sitemap.xml"
grep -Fq 'https://www.bosonit.org/sales-tax-calculator/' "${dist_root}/sitemap.xml"

for slug in mortgage-payment-calculator calorie-deficit-calculator sales-tax-calculator; do
  alias="${CANONICAL_ALIAS_BY_SLUG[$slug]}"

  for relative_path in index.html tool.js styles.css faq-schema.json; do
    test -f "${dist_root}/${alias}/${relative_path}"
    test -f "${dist_root}/utility-sites/${slug}/${relative_path}"
  done

  grep -Fq "\"site_slug\": \"${slug}\"" "${dist_root}/observatory/utility-sites.latest.json"
  grep -Fq "rel=\"canonical\" href=\"https://www.bosonit.org/${alias}/\"" "${dist_root}/${alias}/index.html"
  grep -Fq "RewriteRule ^utility-sites/${slug}/?$ /${alias}/ [R=301,L]" "${dist_root}/.htaccess"
  grep -Fq "RewriteRule ^utility-sites/${slug}/index\\.html$ /${alias}/ [R=301,L]" "${dist_root}/.htaccess"
done

echo "Applied bundled BOS-121 canonical payload to ${dist_root}."
