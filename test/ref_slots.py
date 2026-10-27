#!/usr/bin/env python3
"""Run a reference disassembler over a corpus of 16-bit little-endian words and print
"<byte offset> <len> <text>" lines (the format compare.py reads), in the spelling norm_slots.py
canonicalises.
  ref_slots.py gputils <corpus.bin> <out.txt>   gpdasm -p p16f15386 (gputils 1.5.2): every 14-bit word
  ref_slots.py mame    <corpus.bin> <out.txt>   MAME unidasm -arch pic16c62x, only for the encodings
                                                shared by the classic and the enhanced mid-range core
$GPDASM / $UNIDASM name the tools if they are not on PATH. Offsets are byte offsets in the corpus;
gpdasm prints word addresses, so they are doubled."""
import os, re, struct, subprocess, sys, tempfile
tool, src, outp = sys.argv[1:4]
data = open(src, 'rb').read()
n = len(data) // 2
out = open(outp, 'w')

def ihex(data):
    recs = []
    for off in range(0, len(data), 16):
        d = data[off:off + 16]
        b = bytes([len(d), (off >> 8) & 255, off & 255, 0]) + d
        recs.append(':' + b.hex().upper() + '%02X' % ((-sum(b)) & 255))
    recs.append(':00000001FF')
    return '\n'.join(recs) + '\n'

if tool == 'gputils':
    assert n <= 0x8000
    with tempfile.NamedTemporaryFile('w', suffix='.hex', delete=False) as f:
        f.write(ihex(data))
    res = subprocess.run([os.environ.get('GPDASM', 'gpdasm'), '-p', 'p16f15386', f.name],
                         capture_output=True, text=True).stdout
    os.unlink(f.name)
    for l in res.splitlines():
        m = re.match(r'^([0-9a-f]+):\s+([0-9a-f]{4})\s+(.*)$', l)
        if not m:
            continue
        t = re.sub(r'\s+', ' ', m.group(3).strip())
        out.write('%08x %d %s\n' % (int(m.group(1), 16) * 2, 0 if t.startswith('dw') else 2, t))
else:
    res = subprocess.run([os.environ.get('UNIDASM', 'unidasm'), '-arch', 'pic16c62x', src],
                         capture_output=True, text=True).stdout
    for l in res.splitlines():
        m = re.match(r'^([0-9a-f]{4}): ([0-9a-f]{4})\s+(.*)$', l)
        if not m:
            continue
        a, w, t = int(m.group(1), 16), int(m.group(2), 16) & 0x3fff, m.group(3).strip()
        top = w >> 8
        # shared by the classic and the enhanced core: the byte/bit/call/goto groups below 0x3000 and
        # MOVLW 30, RETLW 34, IORLW 38, ANDLW 39, XORLW 3a, SUBLW 3c, ADDLW 3e
        if not (w < 0x3000 or top in (0x30, 0x34, 0x38, 0x39, 0x3a, 0x3c, 0x3e)):
            continue
        if t.startswith('????'):
            out.write('%08x 0 dw\n' % (a * 2))
            continue
        t = re.sub(r'\s*\([^)]*\)', '', t)                    # Reg$03 (STATUS) -> Reg$03
        t = re.sub(r'Reg\$([0-9a-f]+)', r'0x\1', t)
        t = re.sub(r'\$([0-9a-f]+)', r'0x\1', t)
        t = re.sub(r'\b([0-9a-f]+)h\b', r'0x\1', t, flags=re.I)
        t = re.sub(r',W\b', ',0', t, flags=re.I)
        t = re.sub(r',(F|reg)\b', ',1', t, flags=re.I)
        out.write('%08x 2 %s\n' % (a * 2, re.sub(r'\s+', ' ', t)))
out.close()
