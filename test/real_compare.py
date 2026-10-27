#!/usr/bin/env python3
"""Compare the instructions Ghidra disassembled in a real image (PicRealCheck.java listing) with
gpdasm's disassembly of the same Intel hex file at the same word addresses.
  real_compare.py <listing.txt> <file.hex> <outdir> [explain.py]
Writes slot files (one slot per instruction) and runs compare.py on them."""
import os, re, subprocess, sys, tempfile
lst, hexf, outd = sys.argv[1:4]
here = os.path.dirname(os.path.abspath(__file__))
gh = {}
for l in open(lst):
    a, b, t = l.rstrip('\n').split(' ', 2)
    gh[int(a, 16)] = (bytes.fromhex(b), t)
res = subprocess.run([os.environ.get('GPDASM', 'gpdasm'), '-p', os.environ.get('GPPROC', 'p16f15386'), hexf],
                     capture_output=True, text=True).stdout
gp = {}
for l in res.splitlines():
    m = re.match(r'^([0-9a-f]+):\s+([0-9a-f]{4})\s+(.*)$', l)
    if m:
        t = re.sub(r'\s+', ' ', m.group(3).strip())
        gp[int(m.group(1), 16)] = (0 if t.startswith('dw') else 2, t)
os.makedirs(outd, exist_ok=True)
data = bytearray(2 * (max(gh) + 1))
with open(os.path.join(outd, 'gh.txt'), 'w') as g, open(os.path.join(outd, 'gp.txt'), 'w') as o:
    for a in sorted(gh):
        b, t = gh[a]
        data[2 * a:2 * a + 2] = (b + bytes(2))[:2]
        g.write(f'{a * 2:08x} {len(b)} {t}\n')
        n, rt = gp.get(a, (0, 'dw'))            # gpdasm prints nothing for cells the hex does not define
        o.write(f'{a * 2:08x} {n} {rt}\n')
for n_, tool in (('gh', 'ghidra'), ('gp', 'gputils')):
    subprocess.run(['python3', os.path.join(here, 'norm_slots.py'), tool, os.path.join(outd, n_ + '.txt'),
                    os.path.join(outd, n_ + '_n.txt'), 'nopage'], check=True)
open(os.path.join(outd, 'slots.bin'), 'wb').write(data)
args = ['python3', os.path.join(here, 'compare.py'), os.path.join(outd, 'gh_n.txt'),
        os.path.join(outd, 'gp_n.txt'), os.path.join(outd, 'slots.bin'), '--bits', '16']
if len(sys.argv) > 4:
    args += ['--explain', sys.argv[4]]
sys.exit(subprocess.run(args).returncode)
