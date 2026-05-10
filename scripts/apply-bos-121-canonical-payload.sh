#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  bash ./scripts/apply-bos-121-canonical-payload.sh [options]

Options:
  --dist-root PATH   Dist root to overlay. Defaults to ./dist
  --base-url URL     Source site to snapshot. Defaults to https://www.bosonit.org
  -h, --help         Show help.
EOF
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

dist_root="${REPO_ROOT}/dist"
base_url="https://www.bosonit.org"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dist-root)
      dist_root="${2:-}"
      shift 2
      ;;
    --base-url)
      base_url="${2:-}"
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

for required in curl mkdir mktemp perl rg cp; do
  if ! command -v "${required}" >/dev/null 2>&1; then
    echo "Missing required command: ${required}" >&2
    exit 1
  fi
done

mkdir -p \
  "${dist_root}" \
  "${dist_root}/utility-sites" \
  "${dist_root}/observatory"

fetch_file() {
  local url="$1"
  local output_path="$2"
  curl -fsSL "${url}" -o "${output_path}"
}

strip_cloudflare_injection() {
  local html_path="$1"
  perl -0pi -e 's#\n\s*<script>\(function\(\)\{.*?window\.__CF\$cv\$params.*?</script>\s*</body>#\n  </body>#s' "${html_path}"
}

rewrite_short_alias_html() {
  local html_path="$1"
  local slug="$2"
  local alias="$3"

  strip_cloudflare_injection "${html_path}"

  perl -0pi -e '
    s#https://www\.bosonit\.org/utility-sites/'"${slug}"'/#https://www.bosonit.org/'"${alias}"'/#g;
    s#<a class="brand" href="\.\./">#<a class="brand" href="/utility-sites/">#g;
    s#href="\.\./sales-tax-calculator/"#href="/sales-tax-calculator/"#g;
    s#href="\.\./mortgage-payment-calculator/"#href="/mortgage-calculator/"#g;
    s#href="\.\./calorie-deficit-calculator/"#href="/calorie-calculator/"#g;
  ' "${html_path}"
}

write_file() {
  local output_path="$1"
  mkdir -p "$(dirname "${output_path}")"
  cat > "${output_path}"
}

write_htaccess() {
  write_file "${dist_root}/.htaccess" <<'EOF'
RewriteEngine On
RewriteBase /

# BOS-121 canonical calculator aliases.
RewriteRule ^utility-sites/mortgage-payment-calculator/?$ /mortgage-calculator/ [R=301,L]
RewriteRule ^utility-sites/mortgage-payment-calculator/index\.html$ /mortgage-calculator/ [R=301,L]
RewriteRule ^utility-sites/calorie-deficit-calculator/?$ /calorie-calculator/ [R=301,L]
RewriteRule ^utility-sites/calorie-deficit-calculator/index\.html$ /calorie-calculator/ [R=301,L]
RewriteRule ^utility-sites/sales-tax-calculator/?$ /sales-tax-calculator/ [R=301,L]
RewriteRule ^utility-sites/sales-tax-calculator/index\.html$ /sales-tax-calculator/ [R=301,L]

# Serve real files and directories first.
RewriteCond %{REQUEST_FILENAME} -f [OR]
RewriteCond %{REQUEST_FILENAME} -d
RewriteRule ^ - [L]

# Explicit static routes that must bypass generic homepage fallback.
RewriteRule ^services/?$ /services/index.html [L]
RewriteRule ^control-plane/?$ /control-plane/index.html [L]
RewriteRule ^observatory/control-plane.latest.json$ /observatory/control-plane.latest.json [L]

# Default SPA/static fallback.
RewriteRule . /index.html [L]
EOF
}

write_hub() {
  write_file "${dist_root}/utility-sites/index.html" <<'EOF'
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>BosonIT Utility Calculators</title>
    <link rel="icon" href="data:," />
    <meta
      name="description"
      content="Browse the approved BosonIT utility calculator rollout with short canonical routes for mortgage planning, calorie-deficit estimates, and sales tax math."
    />
    <link rel="canonical" href="https://www.bosonit.org/utility-sites/" />
    <meta property="og:url" content="https://www.bosonit.org/utility-sites/" />
    <style>
      :root {
        color-scheme: light;
        --bg: #f4f6f2;
        --panel: #ffffff;
        --ink: #17211d;
        --muted: #52605a;
        --line: rgba(37, 63, 51, 0.14);
        --accent: #126a52;
      }

      * {
        box-sizing: border-box;
      }

      body {
        margin: 0;
        min-height: 100vh;
        background: linear-gradient(180deg, #fbfcf8 0%, var(--bg) 100%);
        color: var(--ink);
        font-family: "Segoe UI", Helvetica, Arial, sans-serif;
        line-height: 1.5;
      }

      main {
        width: min(960px, calc(100% - 2rem));
        margin: 0 auto;
        padding: 2rem 0 4rem;
      }

      .hero,
      .card {
        background: var(--panel);
        border: 1px solid var(--line);
        border-radius: 24px;
        box-shadow: 0 18px 34px rgba(24, 34, 29, 0.08);
      }

      .hero {
        padding: 1.75rem;
      }

      .eyebrow {
        margin: 0 0 0.5rem;
        color: var(--accent);
        font-size: 0.85rem;
        font-weight: 700;
        letter-spacing: 0.08em;
        text-transform: uppercase;
      }

      h1,
      h2,
      p {
        margin-top: 0;
      }

      .grid {
        display: grid;
        gap: 1rem;
        margin-top: 1.5rem;
      }

      .card {
        display: block;
        padding: 1.25rem;
        color: inherit;
        text-decoration: none;
      }

      .route-chip {
        display: inline-block;
        margin-bottom: 0.75rem;
        padding: 0.3rem 0.65rem;
        border-radius: 999px;
        background: rgba(18, 106, 82, 0.1);
        color: var(--accent);
        font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
        font-size: 0.85rem;
      }

      a:hover .route-chip {
        background: rgba(18, 106, 82, 0.18);
      }

      .note {
        color: var(--muted);
      }
    </style>
  </head>
  <body>
    <main>
      <section class="hero">
        <p class="eyebrow">BOS-121 Canonical Rollout</p>
        <h1>BosonIT Utility Calculators</h1>
        <p>
          This rollout keeps the public utility lane focused on the three approved short canonical
          calculator routes while preserving the archive path and legacy redirects.
        </p>
        <p class="note">
          Approved routes: mortgage payment, calorie deficit, and sales tax.
        </p>
      </section>

      <section class="grid" aria-label="Approved utility calculators">
        <a class="card" href="/mortgage-calculator/">
          <span class="route-chip">/mortgage-calculator/</span>
          <h2>Mortgage Payment Calculator</h2>
          <p>Estimate principal-and-interest payment size instantly on the approved short route.</p>
        </a>

        <a class="card" href="/calorie-calculator/">
          <span class="route-chip">/calorie-calculator/</span>
          <h2>Calorie Deficit Calculator</h2>
          <p>Estimate a calorie deficit target with a short shareable route and transparent assumptions.</p>
        </a>

        <a class="card" href="/sales-tax-calculator/">
          <span class="route-chip">/sales-tax-calculator/</span>
          <h2>Sales Tax Calculator</h2>
          <p>Calculate subtotal, tax, and total instantly on the approved sales tax short route.</p>
        </a>
      </section>
    </main>
  </body>
</html>
EOF
}

write_sitemap() {
  write_file "${dist_root}/sitemap.xml" <<'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://www.bosonit.org/</loc>
  </url>
  <url>
    <loc>https://www.bosonit.org/services/</loc>
  </url>
  <url>
    <loc>https://www.bosonit.org/control-plane/</loc>
  </url>
  <url>
    <loc>https://www.bosonit.org/utility-sites/</loc>
  </url>
  <url>
    <loc>https://www.bosonit.org/mortgage-calculator/</loc>
  </url>
  <url>
    <loc>https://www.bosonit.org/calorie-calculator/</loc>
  </url>
  <url>
    <loc>https://www.bosonit.org/sales-tax-calculator/</loc>
  </url>
</urlset>
EOF
}

write_observatory_snapshot() {
  write_file "${dist_root}/observatory/utility-sites.latest.json" <<'EOF'
{
  "all_pilots_file_complete": true,
  "generated_at_utc": "2026-05-10T00:00:00.000000+00:00",
  "pilot_count": 3,
  "pilots": [
    {
      "cluster_key": "calorie",
      "computation_mode": "calorie-deficit",
      "has_css_ref": true,
      "has_js_ref": true,
      "missing_files": [],
      "preview_url": "/calorie-calculator/",
      "primary_keyword": "calorie deficit calculator",
      "publish_target": "bosonit-site-canonical-rollout",
      "published_files": [
        "index.html",
        "tool.js",
        "styles.css",
        "faq-schema.json"
      ],
      "site_slug": "calorie-deficit-calculator",
      "status": "published"
    },
    {
      "cluster_key": "mortgage",
      "computation_mode": "mortgage-payment",
      "has_css_ref": true,
      "has_js_ref": true,
      "missing_files": [],
      "preview_url": "/mortgage-calculator/",
      "primary_keyword": "mortgage payment calculator",
      "publish_target": "bosonit-site-canonical-rollout",
      "published_files": [
        "index.html",
        "tool.js",
        "styles.css",
        "faq-schema.json"
      ],
      "site_slug": "mortgage-payment-calculator",
      "status": "published"
    },
    {
      "cluster_key": "sales",
      "computation_mode": "sales-tax",
      "has_css_ref": true,
      "has_js_ref": true,
      "missing_files": [],
      "preview_url": "/sales-tax-calculator/",
      "primary_keyword": "sales tax calculator",
      "publish_target": "bosonit-site-canonical-rollout",
      "published_files": [
        "index.html",
        "tool.js",
        "styles.css",
        "faq-schema.json"
      ],
      "site_slug": "sales-tax-calculator",
      "status": "published"
    }
  ],
  "schema_version": "2026-05-10.utility-sites-canonical-rollout.v1",
  "source": "BOS-121 canonical rollout overlay"
}
EOF
}

fetch_route_bundle() {
  local slug="$1"
  local alias="$2"
  local legacy_dir="${dist_root}/utility-sites/${slug}"
  local alias_dir="${dist_root}/${alias}"

  mkdir -p "${legacy_dir}" "${alias_dir}"

  fetch_file "${base_url}/utility-sites/${slug}/index.html" "${legacy_dir}/index.html"
  fetch_file "${base_url}/utility-sites/${slug}/tool.js" "${legacy_dir}/tool.js"
  fetch_file "${base_url}/utility-sites/${slug}/styles.css" "${legacy_dir}/styles.css"
  fetch_file "${base_url}/utility-sites/${slug}/faq-schema.json" "${legacy_dir}/faq-schema.json"
  strip_cloudflare_injection "${legacy_dir}/index.html"

  cp "${legacy_dir}/tool.js" "${alias_dir}/tool.js"
  cp "${legacy_dir}/styles.css" "${alias_dir}/styles.css"
  cp "${legacy_dir}/faq-schema.json" "${alias_dir}/faq-schema.json"
  cp "${legacy_dir}/index.html" "${alias_dir}/index.html"
  rewrite_short_alias_html "${alias_dir}/index.html" "${slug}" "${alias}"
}

verify_output() {
  rg -Fq 'href="/mortgage-calculator/"' "${dist_root}/utility-sites/index.html"
  rg -Fq 'href="/calorie-calculator/"' "${dist_root}/utility-sites/index.html"
  rg -Fq 'href="/sales-tax-calculator/"' "${dist_root}/utility-sites/index.html"
  rg -Fq 'rel="canonical" href="https://www.bosonit.org/mortgage-calculator/"' "${dist_root}/mortgage-calculator/index.html"
  rg -Fq 'rel="canonical" href="https://www.bosonit.org/calorie-calculator/"' "${dist_root}/calorie-calculator/index.html"
  rg -Fq 'rel="canonical" href="https://www.bosonit.org/sales-tax-calculator/"' "${dist_root}/sales-tax-calculator/index.html"
  rg -Fq 'RewriteRule ^utility-sites/mortgage-payment-calculator/?$ /mortgage-calculator/ [R=301,L]' "${dist_root}/.htaccess"
  rg -Fq 'RewriteRule ^utility-sites/calorie-deficit-calculator/?$ /calorie-calculator/ [R=301,L]' "${dist_root}/.htaccess"
  rg -Fq 'RewriteRule ^utility-sites/sales-tax-calculator/?$ /sales-tax-calculator/ [R=301,L]' "${dist_root}/.htaccess"
  rg -Fq '"preview_url": "/mortgage-calculator/"' "${dist_root}/observatory/utility-sites.latest.json"
  rg -Fq '"preview_url": "/calorie-calculator/"' "${dist_root}/observatory/utility-sites.latest.json"
  rg -Fq '"preview_url": "/sales-tax-calculator/"' "${dist_root}/observatory/utility-sites.latest.json"
  rg -Fq 'https://www.bosonit.org/utility-sites/' "${dist_root}/sitemap.xml"
  rg -Fq 'https://www.bosonit.org/mortgage-calculator/' "${dist_root}/sitemap.xml"
  rg -Fq 'https://www.bosonit.org/calorie-calculator/' "${dist_root}/sitemap.xml"
  rg -Fq 'https://www.bosonit.org/sales-tax-calculator/' "${dist_root}/sitemap.xml"
}

fetch_route_bundle "mortgage-payment-calculator" "mortgage-calculator"
fetch_route_bundle "calorie-deficit-calculator" "calorie-calculator"
fetch_route_bundle "sales-tax-calculator" "sales-tax-calculator"
write_htaccess
write_hub
write_sitemap
write_observatory_snapshot
verify_output

echo "BOS-121 canonical overlay applied to ${dist_root}"
