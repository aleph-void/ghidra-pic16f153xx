"""Explanations for decode differences between Ghidra's PIC16F153xx module and gpdasm (gputils 1.5.2,
p16f15386 as the device so that every address is inside the program memory)."""

def classify(off, rn, rt, gn, gt, data):
    w = int.from_bytes(data[off:off + 2], 'little') & 0x3fff
    if 0x0100 <= w <= 0x0102 and gt.lower().startswith('clrw'):
        return 'CLRW with the "x" bits not 11: the data sheet (table 36-3) encodes CLRW as 00 0001 0000 00xx, gpdasm accepts only the form gpasm writes (0x0103)'
    if w == 0x0061 and rt.lower() == 'halt':
        return 'gpdasm decodes 0x0061 as "halt" (ICD instruction); not in the 15325/45 instruction set, so left undefined'
    return None
