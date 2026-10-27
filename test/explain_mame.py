"""Differences between Ghidra's PIC16F153xx module and MAME's PIC16C62x disassembler, which knows
only the classic mid-range instruction set."""

ENHANCED = {'reset', 'callw', 'brw', 'moviw', 'movwi', 'option', 'tris', 'asrf', 'lslf', 'lsrf', 'bra',
            'addwfc', 'subwfb', 'addfsr', 'movlb', 'movlp', 'nop', 'clrw'}

def classify(off, rn, rt, gn, gt, data):
    if rn == 0 and gn and gt.split(' ')[0].lower() in ENHANCED:
        return 'instruction of the enhanced mid-range core (or the nop/clrw "x" encodings); MAME\'s PIC16C62x core predates it'
    return None
