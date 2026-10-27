#!/usr/bin/env python3
"""The assembler pseudo-instructions the module decodes with the context bit doPseudo=1
(BC BNC BZ BNZ SKPC SKPNC SKPZ SKPNZ): gpasm assembles them, Ghidra must decode the same words
back to the same mnemonic and (for the branches) the same target.
  pseudo_check.py <outdir> <testdir>"""
import os, re, subprocess, sys, struct
outd, here = sys.argv[1:3]
asm = '\tprocessor p16f15386\n\torg 0x10\n' + ''.join(
    f'\t{m}{(" 0x30" if m[0] == "b" else "")}\n' for m in
    ['bc', 'bnc', 'bz', 'bnz', 'skpc', 'skpnc', 'skpz', 'skpnz']) + '\tend\n'
open(outd + '/pseudo.asm', 'w').write(asm)
subprocess.run(['gpasm', '-o', outd + '/pseudo.hex', outd + '/pseudo.asm'], check=True, capture_output=True)
img = bytearray(0x100)
for l in open(outd + '/pseudo.hex'):
    l = l.strip()
    if l.startswith(':') and l[7:9] == '00':
        n, a = int(l[1:3], 16), int(l[3:7], 16)
        img[a:a + n] = bytes.fromhex(l[9:9 + 2 * n])
open(outd + '/pseudo.bin', 'wb').write(img)
subprocess.run([here + '/ghidra-slots.sh', 'PIC-16:LE:16:PIC-16F153xx', outd + '/pseudo.bin', '2',
                outd + '/pseudo_gh.txt', 'doPseudo=1'], check=True)
got = [l.split(' ', 2)[2].strip() for l in open(outd + '/pseudo_gh.txt')][0x10:0x10 + 12]
# slots: bc(+goto) bnc(+goto) bz(+goto) bnz(+goto) skpc skpnc skpz skpnz
want = ['bc 0x30', 'goto 0x30', 'bnc 0x30', 'goto 0x30', 'bz 0x30', 'goto 0x30', 'bnz 0x30', 'goto 0x30',
        'skpc', 'skpnc', 'skpz', 'skpnz']
# gpasm expands the branch pseudo-ops into two words; Ghidra decodes the first word together with the
# goto, so every second slot is the goto itself
seq = []
i = 0
words = [got[k] for k in range(12)]
ok = True
exp = [('bc', 2), ('bnc', 2), ('bz', 2), ('bnz', 2), ('skpc', 1), ('skpnc', 1), ('skpz', 1), ('skpnz', 1)]
pos = 0
for name, n in exp:
    g = words[pos].lower()
    if not g.startswith(name):
        print('pseudo-instruction %s: Ghidra decodes %r' % (name, words[pos])); ok = False
    if n == 2 and int(g.split()[1], 0) != 0x30:
        print('pseudo-instruction %s: wrong target in %r' % (name, words[pos])); ok = False
    pos += n
print('pseudo-instructions (doPseudo=1) vs gpasm encodings: %s' % ('8/8 agree' if ok else 'DIFFER'))

# CALL/GOTO targets come from the context field pcHi (PCLATH<6:3> as MOVLP left it)
img = bytearray(0x40)
img[0:6] = struct.pack('<3H', 0x2805, 0x2005, 0x31a8)       # goto 5; call 5; movlp 0x28
subprocess.run([here + '/ghidra-slots.sh', 'PIC-16:LE:16:PIC-16F153xx', outd + '/ctx.bin', '2',
                outd + '/ctx_gh.txt', 'pcHi=5'], check=True) if open(outd + '/ctx.bin', 'wb').write(img) else None
c = [l.split(' ', 2)[2].strip() for l in open(outd + '/ctx_gh.txt')][:2]
good = c == ['GOTO 0x2805', 'CALL 0x2805']
print('GOTO/CALL with pcHi=5: %s -> %s' % (c, 'ok' if good else 'WRONG'))
sys.exit(0 if (ok and good) else 1)
