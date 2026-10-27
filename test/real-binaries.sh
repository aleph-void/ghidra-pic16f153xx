#!/usr/bin/env bash
# Real code for the PIC16F153xx module: test/real-binaries.sh <workdir>
#  1. fetches two third-party Intel hex files (MIT-licensed bootloader stubs for the PIC16F15344/5,
#     github.com/react66/bootloader-pic16 at a pinned commit, SHA-256 checked, never committed)
#  2. assembles test/real/algos.asm (CRC-16, 16x16 multiply, XTEA, bubble sort, computed-goto table)
#     with gpasm and runs it in the p-code emulator against reference values computed in Python
#  3. imports all three hex files with Ghidra's Intel Hex loader (auto-analysis), reports
#     instructions/functions/bookmarks/decompile failures, and compares the disassembly with
#     gpdasm at the same addresses
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
source "$HERE/env.sh"
W=$(readlink -m "${1:?workdir}")
mkdir -p "$W"
rc=0
COMMIT=6809d77112e8c9676efb7709bd81369acff47188
BASE=https://raw.githubusercontent.com/react66/bootloader-pic16/$COMMIT/pic16f15344/hex_files
fetch() {
	[[ -s $W/$1 ]] || curl -sfL -o "$W/$1" "$BASE/$1"
	echo "$2  $W/$1" | sha256sum -c --quiet - || { echo "checksum mismatch for $1"; rc=1; }
}
fetch stub344_r02.hex 7853d90f9798531b3d0b765ea895fa0b3e4348c3890e19e8d8ed3700dd3bb12e
fetch stub345_r02.hex 0dea9edb0911409efbb3f11f891f201d00d86aa1a25b7c30801d6ee69cf5633b

echo "== algos.asm: emulator vs Python reference"
python3 "$HERE/real/algos.py" "$W/algos" >/dev/null
"$HERE/real-emu.sh" "$W/algos/algos-cases.txt" "$W/algos" | tail -8 || rc=1

for f in "$W/stub344_r02.hex" "$W/stub345_r02.hex" "$W/algos/algos.hex"; do
	n=$(basename "$f" .hex)
	echo "== import $n"
	P=$(mktemp -d "${TMPDIR:-/tmp}/pic-real.XXXXXX")
	"$GHIDRA_INSTALL_DIR/support/analyzeHeadless" "$P" p -import "$f" -loader IntelHexLoader \
		-processor PIC-16:LE:16:PIC-16F153xx -scriptPath "$HERE" \
		-postScript PicRealCheck.java "$W/$n.sum" "$W/$n.lst" "$W/$n.dec" 120 -deleteProject >"$P/log.txt" 2>&1 \
		|| { tail -30 "$P/log.txt"; rc=1; }
	rm -rf "$P"
	sed 's/^/   /' "$W/$n.sum" | grep -E "functions:|instructions:|bad-instruction|error bookmarks|decompile:"
	grep -q "bad-instruction bookmarks: 0" "$W/$n.sum" || rc=1
	grep -q "error bookmarks: 0" "$W/$n.sum" || rc=1
	grep -q " 0 failed, 0 timed out" "$W/$n.sum" || rc=1
	python3 "$HERE/real_compare.py" "$W/$n.lst" "$f" "$W/cmp_$n" "$HERE/explain_gputils.py" | head -3 | sed 's/^/   gpdasm: /' || rc=1
done
exit $rc
