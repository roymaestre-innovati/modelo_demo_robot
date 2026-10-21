#!/usr/bin/env bash
# Convierte SVG a PNG con Chrome headless (no hay rsvg-convert ni inkscape).
# Uso: concepts/svg2png.sh archivo.svg [mas.svg ...]
set -euo pipefail
CHROME=${CHROME:-google-chrome}
for f in "$@"; do
  abs=$(realpath "$f")
  w=$(grep -o 'width="[0-9]*"' "$abs" | head -1 | grep -o '[0-9]*')
  h=$(grep -o 'height="[0-9]*"' "$abs" | head -1 | grep -o '[0-9]*')
  "$CHROME" --headless=new --disable-gpu --hide-scrollbars --no-sandbox \
    --window-size="$w,$h" --screenshot="${abs%.svg}.png" "file://$abs" >/dev/null 2>&1
  echo "${abs%.svg}.png"
done
