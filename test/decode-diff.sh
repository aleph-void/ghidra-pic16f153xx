#!/usr/bin/env bash
# Decode differential: test/decode-diff.sh <outdir>
# All 16384 words of the 14-bit instruction set (test/gen_corpus.py) are decoded by Ghidra
# (PIC-16:LE:16:PIC-16F153xx) and by gpdasm (gputils, $GPDASM, device p16f15386) and, for the
# encodings the classic and enhanced mid-range cores share, by MAME unidasm -arch pic16c62x.
# Every difference must fall in an explained class (explain_gputils.py, explain_mame.py).
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
source "$HERE/env.sh"
OUTD=$(readlink -m "${1:-${TMPDIR:-/tmp}/pic16f153xx-decode}")
LANG_ID=PIC-16:LE:16:PIC-16F153xx
mkdir -p "$OUTD"
rc=0
python3 "$HERE/gen_corpus.py" "$OUTD/all.bin"
"$HERE/ghidra-slots.sh" $LANG_ID "$OUTD/all.bin" 2 "$OUTD/gh.txt"
# the slot dump decodes with the default context of the program (pcHi = 0): CALL/GOTO targets
# are checked against page 0
python3 "$HERE/norm_slots.py" ghidra "$OUTD/gh.txt" "$OUTD/gh_n.txt" nopage
if command -v "${GPDASM:-gpdasm}" >/dev/null; then
	python3 "$HERE/ref_slots.py" gputils "$OUTD/all.bin" "$OUTD/gp.txt"
	python3 "$HERE/norm_slots.py" gputils "$OUTD/gp.txt" "$OUTD/gp_n.txt"
	python3 "$HERE/compare.py" "$OUTD/gh_n.txt" "$OUTD/gp_n.txt" "$OUTD/all.bin" --bits 16 \
		--explain "$HERE/explain_gputils.py" >"$OUTD/cmp_gputils.txt" || rc=1
	echo "gpdasm (gputils), all 16384 words: $(head -1 "$OUTD/cmp_gputils.txt")"
	tail -n +2 "$OUTD/cmp_gputils.txt" | sed 's/^/   /'
else
	echo "gpdasm not found (set GPDASM): skipped"
fi
if command -v "${UNIDASM:-unidasm}" >/dev/null; then
	python3 "$HERE/ref_slots.py" mame "$OUTD/all.bin" "$OUTD/mame.txt"
	python3 "$HERE/norm_slots.py" gputils "$OUTD/mame.txt" "$OUTD/mame_n.txt"
	python3 "$HERE/compare.py" "$OUTD/gh_n.txt" "$OUTD/mame_n.txt" "$OUTD/all.bin" --bits 16 \
		--explain "$HERE/explain_mame.py" >"$OUTD/cmp_mame.txt" || rc=1
	echo "MAME unidasm -arch pic16c62x, shared encodings: $(head -1 "$OUTD/cmp_mame.txt")"
	tail -n +2 "$OUTD/cmp_mame.txt" | sed 's/^/   /'
else
	echo "unidasm not found: skipped"
fi
# the pseudo-instructions (context bit doPseudo) against gpasm's encodings of BC/BNC/BZ/BNZ/SKP*
if command -v "${GPASM:-gpasm}" >/dev/null; then
	python3 "$HERE/pseudo_check.py" "$OUTD" "$HERE" || rc=1
fi
exit $rc
