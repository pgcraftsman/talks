#!/usr/bin/env bash
# Build the PGDay NYC 2026 deck: renumber, marp (html, pdf, png), scan.
# Runs on macOS (Google Chrome.app) and Linux (google-chrome). Call from anywhere.
# Exit 1 from scan.py means a slide clips: stop and fix before committing outputs.
set -euo pipefail
cd "$(dirname "$0")"

# Chrome for the pdf and png renders. Honour CHROME_PATH when already set.
if [ -z "${CHROME_PATH:-}" ]; then
  for c in "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
           /usr/bin/google-chrome /usr/bin/google-chrome-stable \
           /usr/bin/chromium /usr/bin/chromium-browser; do
    if [ -x "$c" ]; then CHROME_PATH="$c"; break; fi
  done
fi
if [ ! -x "${CHROME_PATH:-}" ]; then
  echo "build.sh: no Chrome found; set CHROME_PATH" >&2; exit 2
fi
export CHROME_PATH

# Python 3.12 venv at ../.venv (matplotlib for scan.py, pypdf). Created on first run.
VENV=../.venv
PIP_INDEX=${PIP_INDEX:-https://pypi.org/simple}
if [ ! -x "$VENV/bin/python" ]; then
  if command -v uv >/dev/null 2>&1; then
    uv venv --python 3.12 "$VENV"
    uv pip install --python "$VENV/bin/python" -i "$PIP_INDEX" matplotlib pypdf
  else
    python3 -m venv "$VENV"
    "$VENV/bin/pip" install -q -i "$PIP_INDEX" matplotlib pypdf
  fi
fi
PY="$VENV/bin/python"

# marp-cli, pinned in package.json. The chromium-bidi override there is what lets
# npm install succeed on registries that lack the chromium-bidi version puppeteer asks for.
if [ ! -x node_modules/.bin/marp ]; then
  npm install --no-fund --no-audit
fi
MARP=node_modules/.bin/marp

"$PY" -I ../charts/make_pool_exhaustion.py >/dev/null   # writes charts/pool-exhaustion.svg and the inline copy in slides.md
"$PY" -I ../charts/make_pool_calm.py >/dev/null         # writes charts/pool-calm.svg and the inline copy in slides.md (OCON2)
"$PY" -I ../charts/make_pool_bloat.py >/dev/null        # writes charts/pool-bloat.svg and the inline copy in slides.md (MANIM)
"$PY" -I ../charts/make_mvcc_primer.py >/dev/null       # writes charts/mvcc-primer.svg, charts/mvcc-end-state.svg and the inline copy in slides.md
"$PY" -I ../charts/make_mvcc_year.py >/dev/null         # writes charts/mvcc-year.svg
"$PY" -I ../charts/make_mvcc_day1.py >/dev/null         # writes charts/mvcc-day1.svg
"$PY" -I renumber.py
"$MARP" slides.md --theme-set pgslides.css --html --allow-local-files -o slides.html </dev/null
"$MARP" slides.md --theme-set pgslides.css --html --allow-local-files --pdf -o slides.pdf </dev/null
rm -f img/slide.*.png
"$MARP" slides.md --theme-set pgslides.css --html --allow-local-files --images png -o img/slide.png </dev/null
"$PY" scan.py
