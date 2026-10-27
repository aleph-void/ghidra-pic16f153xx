#!/usr/bin/env bash
# PIC16F153xx module tests:
#   1. the .slaspec compiles
#   2. p-code emulator cases (test/emu/cases.txt, hand-computed results from the data sheet) on
#      PIC-16:LE:16:PIC-16F153xx, and a copy with one deliberately wrong expectation, which must
#      be the only failure
#   3. every-entry decode test (CoverageCheck.java, two seeds)
#   4. decode differential: all 16384 instruction words against gpdasm (gputils) and, for the shared
#      classic encodings, MAME unidasm; assembler pseudo-instructions against gpasm
#   5. with --real <workdir>: test/real-binaries.sh (third-party and self-built firmware)
#
#   test/run-tests.sh [--real <workdir>] [outdir]
#
# Environment: GHIDRA_INSTALL_DIR (Ghidra 12.1.x/12.2 whose Ghidra/Processors/PIC16F153xx is, or
# links to, this module directory), JAVA_HOME (JDK 21+; 25 for Ghidra 12.2), gpdasm/gpasm (gputils
# 1.5.x) and unidasm (MAME tools) on PATH or in $GPDASM/$GPASM/$UNIDASM; steps whose tool is
# missing are skipped. TMPDIR must not contain a path component starting with a dot.
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
MOD=$(cd "$HERE/.." && pwd)
source "$HERE/env.sh"
REAL=
if [[ ${1:-} == --real ]]; then
	REAL=$(readlink -m "$2")
	shift 2
fi
OUT=$(readlink -m "${1:-${TMPDIR:-/tmp}/pic16f153xx-tests}")
mkdir -p "$OUT"
rc=0

echo "== 1. compile"
for s in "$MOD"/data/languages/*.slaspec; do
	"$GHIDRA_INSTALL_DIR/support/sleigh" "$s" >"$OUT/sleigh.log" 2>&1 || { tail -20 "$OUT/sleigh.log"; rc=1; }
	grep -E "ERROR" "$OUT/sleigh.log" && rc=1
done
ls -l "$MOD"/data/languages/*.sla | awk '{print "   " $5, $9}'

echo "== 2. emulator"
"$HERE/emu-test.sh" "$OUT/emu" || rc=1
"$HERE/emu-test.sh" --broken "$OUT/emu" || rc=1
grep -E "emulation \(" "$OUT/emu/emu.txt" | sed 's/^/   /'

echo "== 3. every-entry decode test"
head -c 64 /dev/zero >"$OUT/zero.bin"
for seed in 1 2; do
	PIC_GHIDRA_SETTINGS="${TMPDIR:-/tmp}/pic16f153xx-settings-$seed" \
		"$HERE/ghidra-script.sh" raw PIC-16:LE:16:PIC-16F153xx "$OUT/zero.bin" CoverageCheck.java "$OUT/cov_$seed.txt" 256 "$seed" &
done
wait
tot=$(sed -n 's/^coverage: \([0-9]*\) constructors.*/\1/p' "$OUT/cov_1.txt")
un=$( (cat "$OUT"/cov_*.txt | grep '^unreached' || true) | sort | uniq -c | awk '$1==2' | wc -l)
echo "   $((tot - un))/$tot constructors reached"
(cat "$OUT"/cov_*.txt | grep '^unreached' || true) | sort | uniq -c | awk '$1==2 {print "   " $0}'
((un == 0)) || rc=1

echo "== 4. decode differential"
"$HERE/decode-diff.sh" "$OUT/decode" || rc=1

if [[ -n $REAL ]]; then
	echo "== 5. real code"
	"$HERE/real-binaries.sh" "$REAL" || rc=1
fi
((rc == 0)) && echo "all tests passed" || echo "FAILURES"
exit $rc
