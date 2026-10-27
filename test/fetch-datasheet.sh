#!/usr/bin/env bash
# Fetch Microchip's PIC16(L)F15325/45 data sheet (DS40001865D) for gen_pspec.py and the manual
# cross-checks. It is Microchip's copyrighted document: it is read here, never committed.
#   test/fetch-datasheet.sh <outdir>      -> <outdir>/ds.pdf and <outdir>/ds.txt (pdftotext -layout)
set -euo pipefail
OUT=${1:?outdir}
mkdir -p "$OUT"
URL=https://ww1.microchip.com/downloads/en/DeviceDoc/PIC16-L-F15325-45-Data-Sheet-40001865D.pdf
SHA=3b64d0041cdc8e47177d3f7252a62de8c1a879a4a69442c5ec28c72fce316366
curl -sL -A "Mozilla/5.0" -o "$OUT/ds.pdf" "$URL"
echo "$SHA  $OUT/ds.pdf" | sha256sum -c -
pdftotext -layout "$OUT/ds.pdf" "$OUT/ds.txt"
