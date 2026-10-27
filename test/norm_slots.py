#!/usr/bin/env python3
"""Rewrite a slot dump ("<byte offset> <len> <text>") into one canonical spelling so that
Ghidra's PIC16F153xx disassembly and gpdasm's (gputils) can be compared by compare.py.

  norm_slots.py ghidra|gputils <in.txt> <out.txt> [nopage]

Both sides become "<mnemonic> <op>,<op>" with every operand a number (hex): register names
become their core-register numbers (INDF0=0 INDF1=1 PCL=2 STATUS=3 FSR0L=4 FSR0H=5 FSR1L=6
FSR1H=7 BSR=8 W/WREG=9 PCLATH=0xa INTCON=0xb), "w"/"f" become d=0/1, STATUS/INTCON bit names
become bit numbers, FSR0/FSR1 become 0/1, gputils' ".N" decimals become numbers. Ghidra prints
the resolved target of CALL/GOTO (page << 11 | k11), gputils k11: the target is reduced to k11, after
checking that its page is the page of the instruction (not with 'nopage', for real binaries whose
code sets PCLATH)."""
import re, sys

REG = {'indf0': 0, 'indf1': 1, 'pcl': 2, 'status': 3, 'fsr0l': 4, 'fsr0h': 5, 'fsr1l': 6, 'fsr1h': 7,
       'bsr': 8, 'w': 9, 'wreg': 9, 'pclatch': 10, 'pclath': 10, 'intcon': 11}
BITS = {'c': 0, 'dc': 1, 'z': 2, 'pd': 3, 'to': 4, 'intedg': 0, 'peie': 6, 'gie': 7}

def norm(tool, text, off=None):
    t = text.strip().lower()
    if not t or t.startswith('dw'):
        return t
    mn, _, ops = t.partition(' ')
    ops = ops.strip()
    if tool == 'gputils':
        ops = re.sub(r'\.(\d+)', r'\1', ops)           # .5 -> 5 (decimal)
        ops = re.sub(r'(?<![\w.])(\d+)(?=\[)', r'\1', ops)
        # decimal numbers written by gputils after a dot are plain decimals; others are 0x..
        ops = ops.replace('fsr', '')
        if mn == 'addfsr':       # gputils prints the address of FSRnL (4 or 6), not n
            ops = re.sub(r'^4\b', '0', re.sub(r'^6\b', '1', ops))
        if mn == 'tris':         # gputils prints the whole low byte of the opcode
            ops = '%d' % (int(ops, 16) - 0x60)
    else:
        ops = ops.replace('#', '')
        ops = re.sub(r'fsr([01])(?!\w)', r'\1', ops)
        ops = re.sub(r'\b(indf0|indf1|pcl|status|fsr0l|fsr0h|fsr1l|fsr1h|bsr|wreg|pclath|intcon|w)\b',
                     lambda m: str(REG[m.group(1)]) if mn in ('bcf', 'bsf', 'btfsc', 'btfss') and False else str(REG[m.group(1)]), ops)
        ops = re.sub(r'\b(intedg|peie|gie|dc|pd|to|c|z)\b', lambda m: str(BITS[m.group(1)]), ops)
        ops = re.sub(r',\s*(w)\b', ',0', ops)
    # 'w'/'f' destination of Ghidra: after register substitution 'w' became 9 -> fix below
    if tool == 'ghidra' and mn in ('call', 'goto', 'bc', 'bnc', 'bz', 'bnz'):
        # Ghidra prints the resolved target (pcHi << 11 | k11); gputils prints k11. The page must be
        # the page of the instruction itself (pcHi starts as the page number and no MOVLP is in play).
        m = re.match(r'^(0x[0-9a-f]+|\d+)$', ops)
        if m:
            tgt = int(ops, 0)
            ops = '0x%x' % (tgt & 0x7ff) if (off is None or (tgt >> 11) == ((off // 2) >> 11)) else 'PAGE-MISMATCH %s' % ops
    return (mn + ' ' + ops).strip()

def main():
    tool, src, dst = sys.argv[1:4]
    nopage = len(sys.argv) > 4 and sys.argv[4] == 'nopage'
    out = open(dst, 'w')
    for line in open(src):
        p = line.rstrip('\n').split(' ', 2)
        text = p[2] if len(p) > 2 else ''
        if tool == 'ghidra':
            # destination designators are printed as ",w" / ",f"
            text = re.sub(r',(w)$', ',0', text.strip(), flags=re.I)
            text = re.sub(r',(f)$', ',1', text, flags=re.I)
        out.write('%s %s %s\n' % (p[0], p[1], norm(tool, text, None if nopage else int(p[0], 16))))

if __name__ == '__main__':
    main()
