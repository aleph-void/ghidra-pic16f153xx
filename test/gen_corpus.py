#!/usr/bin/env python3
"""Write every 14-bit instruction word (0x0000-0x3fff) as a little-endian 16-bit cell:
the whole instruction set can be enumerated, so no random sampling is needed.
  gen_corpus.py <out.bin>"""
import struct, sys
open(sys.argv[1], 'wb').write(b''.join(struct.pack('<H', w) for w in range(0x4000)))
