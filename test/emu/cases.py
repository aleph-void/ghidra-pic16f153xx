#!/usr/bin/env python3
"""Emulator cases for the PIC16F153xx module. Each case is assembly (assembled once with gpasm from
gputils at org 0x100 for p16f15386; the machine code is kept in cases.txt, so the test needs no
toolchain), initial registers/memory, and results worked out by hand from the instruction
descriptions in the PIC16(L)F15325/45 data sheet (DS40001865D, chapter 36 and section 4).

  cases.py --assemble        regenerate cases.txt (needs gpasm)
  cases.py --broken          print cases.txt with one expectation made wrong
The program is placed at CODE:0100 (word address) and runs until the PC reaches 0100 plus the
length of the part before a "---" line (or the address given by 'end'). Data memory is zero,
registers are zero unless set. Flags are bits of STATUS: C=0 DC=1 Z=2 PD=3 TO=4."""
import os, re, subprocess, sys, tempfile

# (name, asm, set, expect[, end-address])
CASES = [
 # ---- literal ALU
 ('addlw_carry', 'movlw 0xff\n addlw 1', {}, {'W': 0, 'C': 1, 'DC': 1, 'Z': 1}),
 ('addlw_dc', 'addlw 1', {'W': 0x0f}, {'W': 0x10, 'C': 0, 'DC': 1, 'Z': 0}),
 ('addlw_clears_flags', 'addlw 0x21', {'W': 0x12, 'C': 1, 'DC': 1, 'Z': 1}, {'W': 0x33, 'C': 0, 'DC': 0, 'Z': 0}),
 ('sublw_simple', 'sublw 5', {'W': 3}, {'W': 2, 'C': 1, 'DC': 1, 'Z': 0}),
 ('sublw_borrow', 'sublw 5', {'W': 7}, {'W': 0xfe, 'C': 0, 'DC': 0, 'Z': 0}),
 ('sublw_digit_borrow', 'sublw 0x10', {'W': 0x0f}, {'W': 1, 'C': 1, 'DC': 0, 'Z': 0}),
 ('sublw_zero', 'sublw 0x80', {'W': 0x80}, {'W': 0, 'C': 1, 'DC': 1, 'Z': 1}),
 ('andlw_zero', 'andlw 0x0f', {'W': 0xf0}, {'W': 0, 'Z': 1}),
 ('iorlw_clears_z', 'iorlw 0xf0', {'W': 0x0f, 'Z': 1}, {'W': 0xff, 'Z': 0}),
 ('xorlw_zero', 'xorlw 0xff', {'W': 0xff}, {'W': 0, 'Z': 1}),
 ('movlw_keeps_flags', 'movlw 0x7e\n movwf 0x20', {'Z': 0, 'C': 1}, {'W': 0x7e, 'DATA:20': 0x7e, 'Z': 0, 'C': 1}),
 # ---- byte-oriented ALU, flags
 ('addwf_to_f', 'addwf 0x20,f', {'W': 1, 'DATA:20': 0x7f}, {'DATA:20': 0x80, 'W': 1, 'C': 0, 'DC': 1, 'Z': 0}),
 ('addwf_to_w_zero', 'addwf 0x20,w', {'W': 0xf0, 'DATA:20': 0x10}, {'W': 0, 'DATA:20': 0x10, 'C': 1, 'DC': 0, 'Z': 1}),
 ('addwfc_carry_in', 'addwfc 0x20,w', {'W': 1, 'DATA:20': 1, 'C': 1}, {'W': 3, 'C': 0, 'DC': 0, 'Z': 0}),
 ('addwfc_carry_out', 'addwfc 0x20,f', {'W': 0xff, 'DATA:20': 0, 'C': 1}, {'DATA:20': 0, 'C': 1, 'DC': 1, 'Z': 1}),
 ('subwf_simple', 'subwf 0x20,w', {'W': 3, 'DATA:20': 5}, {'W': 2, 'C': 1, 'DC': 1, 'Z': 0}),
 ('subwf_borrow', 'subwf 0x20,w', {'W': 5, 'DATA:20': 3}, {'W': 0xfe, 'C': 0, 'DC': 0, 'Z': 0}),
 ('subwf_equal', 'subwf 0x20,f', {'W': 0x44, 'DATA:20': 0x44}, {'DATA:20': 0, 'C': 1, 'DC': 1, 'Z': 1}),
 ('subwf_digit_borrow_only', 'subwf 0x20,w', {'W': 1, 'DATA:20': 0x10}, {'W': 0x0f, 'C': 1, 'DC': 0, 'Z': 0}),
 ('subwf_borrow_no_digit_borrow', 'subwf 0x20,w', {'W': 0x11, 'DATA:20': 2}, {'W': 0xf1, 'C': 0, 'DC': 1, 'Z': 0}),
 ('subwfb_borrow_in', 'subwfb 0x20,w', {'W': 1, 'DATA:20': 0x10, 'C': 0}, {'W': 0x0e, 'C': 1, 'DC': 0, 'Z': 0}),
 ('subwfb_no_borrow_in', 'subwfb 0x20,w', {'W': 1, 'DATA:20': 0x10, 'C': 1}, {'W': 0x0f, 'C': 1, 'DC': 0, 'Z': 0}),
 ('subwfb_borrow_out', 'subwfb 0x20,w', {'W': 0, 'DATA:20': 0, 'C': 0}, {'W': 0xff, 'C': 0, 'DC': 0, 'Z': 0}),
 ('subwfb_zero', 'subwfb 0x20,w', {'W': 3, 'DATA:20': 4, 'C': 0}, {'W': 0, 'C': 1, 'DC': 1, 'Z': 1}),
 ('andwf', 'andwf 0x20,f', {'W': 0x3c, 'DATA:20': 0xa5}, {'DATA:20': 0x24, 'Z': 0}),
 ('iorwf', 'iorwf 0x20,w', {'W': 0x3c, 'DATA:20': 0xa5}, {'W': 0xbd, 'DATA:20': 0xa5}),
 ('xorwf', 'xorwf 0x20,f', {'W': 0x3c, 'DATA:20': 0xa5}, {'DATA:20': 0x99}),
 ('comf_zero', 'comf 0x20,w', {'DATA:20': 0xff}, {'W': 0, 'DATA:20': 0xff, 'Z': 1}),
 ('decf_to_zero', 'decf 0x20,f', {'DATA:20': 1}, {'DATA:20': 0, 'Z': 1}),
 ('decf_wrap', 'decf 0x20,f', {'DATA:20': 0, 'Z': 1}, {'DATA:20': 0xff, 'Z': 0}),
 ('incf_wrap', 'incf 0x20,f', {'DATA:20': 0xff}, {'DATA:20': 0, 'Z': 1}),
 ('movf_zero', 'movf 0x20,w', {'W': 5, 'DATA:20': 0}, {'W': 0, 'Z': 1}),
 ('movf_f_tests_z', 'movf 0x20,f', {'DATA:20': 0x80}, {'DATA:20': 0x80, 'Z': 0}),
 ('asrf_negative', 'asrf 0x20,w', {'DATA:20': 0x81}, {'W': 0xc0, 'C': 1, 'Z': 0}),
 ('asrf_zero', 'asrf 0x20,f', {'DATA:20': 1}, {'DATA:20': 0, 'C': 1, 'Z': 1}),
 ('lslf_carry', 'lslf 0x20,w', {'DATA:20': 0x81}, {'W': 2, 'C': 1, 'Z': 0}),
 ('lslf_zero', 'lslf 0x20,f', {'DATA:20': 0x80}, {'DATA:20': 0, 'C': 1, 'Z': 1}),
 ('lsrf_carry', 'lsrf 0x20,w', {'DATA:20': 0x81}, {'W': 0x40, 'C': 1, 'Z': 0}),
 ('lsrf_zero', 'lsrf 0x20,f', {'DATA:20': 1}, {'DATA:20': 0, 'C': 1, 'Z': 1}),
 ('rlf_through_carry', 'rlf 0x20,f', {'DATA:20': 0x80, 'C': 1, 'Z': 0}, {'DATA:20': 1, 'C': 1, 'Z': 0}),
 ('rlf_zero_keeps_z', 'rlf 0x20,f', {'DATA:20': 0x80, 'C': 0, 'Z': 0}, {'DATA:20': 0, 'C': 1, 'Z': 0}),
 ('rrf_through_carry', 'rrf 0x20,f', {'DATA:20': 1, 'C': 1}, {'DATA:20': 0x80, 'C': 1}),
 ('rrf_clear_carry', 'rrf 0x20,w', {'DATA:20': 2, 'C': 0, 'Z': 1}, {'W': 1, 'C': 0, 'Z': 1}),
 ('swapf_keeps_flags', 'swapf 0x20,f', {'DATA:20': 0xa5, 'Z': 1, 'C': 1}, {'DATA:20': 0x5a, 'Z': 1, 'C': 1}),
 ('clrf_sets_z', 'clrf 0x20', {'DATA:20': 0x55}, {'DATA:20': 0, 'Z': 1}),
 ('clrw_sets_z', 'clrw', {'W': 5}, {'W': 0, 'Z': 1}),
 # ---- STATUS as destination, bit instructions
 ('clrf_status', 'clrf 3', {'STATUS': 0x1b}, {'STATUS': 0x1f}),
 ('addwf_status_dest', 'addwf 3,f', {'STATUS': 0x10, 'W': 0x10}, {'STATUS': 0x10}),
 ('movwf_status', 'movwf 3', {'W': 7}, {'STATUS': 7}),
 ('bsf_status_c', 'bsf 3,0', {}, {'C': 1}),
 ('bcf_status_z', 'bcf 3,2', {'Z': 1, 'C': 1}, {'Z': 0, 'C': 1}),
 ('bsf_intcon_gie', 'bsf 0x0b,7', {}, {'INTCON': 0x80}),
 ('bcf_bit', 'bcf 0x20,3', {'DATA:20': 0xff}, {'DATA:20': 0xf7}),
 ('bsf_bit', 'bsf 0x21,7', {}, {'DATA:21': 0x80}),
 ('clrwdt_flags', 'clrwdt', {}, {'TO': 1, 'PD': 1, 'PCODEOPS': 1}),
 ('sleep_flags', 'sleep', {'PD': 1}, {'TO': 1, 'PD': 0, 'PCODEOPS': 1}),
 # ---- skips
 ('incfsz_skips', 'incfsz 0x20,f\n incf 0x21,f\n incf 0x21,f', {'DATA:20': 0xff}, {'DATA:20': 0, 'DATA:21': 1}),
 ('incfsz_no_skip', 'incfsz 0x20,f\n incf 0x21,f\n incf 0x21,f', {'DATA:20': 1}, {'DATA:20': 2, 'DATA:21': 2}),
 ('decfsz_skips', 'decfsz 0x20,w\n incf 0x21,f\n incf 0x21,f', {'DATA:20': 1}, {'W': 0, 'DATA:20': 1, 'DATA:21': 1}),
 ('decfsz_no_skip', 'decfsz 0x20,f\n incf 0x21,f\n incf 0x21,f', {'DATA:20': 2}, {'DATA:20': 1, 'DATA:21': 2}),
 ('btfsc_skips_on_clear', 'btfsc 0x20,4\n incf 0x21,f\n incf 0x21,f', {'DATA:20': 0x0f}, {'DATA:21': 1}),
 ('btfsc_no_skip_on_set', 'btfsc 0x20,4\n incf 0x21,f\n incf 0x21,f', {'DATA:20': 0x10}, {'DATA:21': 2}),
 ('btfss_skips_on_set', 'btfss 0x20,0\n incf 0x21,f\n incf 0x21,f', {'DATA:20': 1}, {'DATA:21': 1}),
 ('btfss_no_skip_on_clear', 'btfss 0x20,0\n incf 0x21,f\n incf 0x21,f', {'DATA:20': 0}, {'DATA:21': 2}),
 ('btfsc_status_z', 'btfsc 3,2\n incf 0x21,f\n incf 0x21,f', {'Z': 1}, {'DATA:21': 2}),
 ('skip_discards_a_skip', 'btfsc 0x20,0\n btfsc 0x21,0\n incf 0x22,f\n incf 0x22,f', {'DATA:20': 0, 'DATA:21': 0}, {'DATA:22': 2}),
 ('skip_chain_second_taken', 'btfsc 0x20,0\n btfsc 0x21,0\n incf 0x22,f\n incf 0x22,f', {'DATA:20': 1, 'DATA:21': 0}, {'DATA:22': 1}),
 ('skip_chain_btfss', 'btfss 0x20,0\n btfss 0x21,0\n incf 0x22,f\n incf 0x22,f', {'DATA:20': 0, 'DATA:21': 1}, {'DATA:22': 1}),
 ('tris_a', 'tris 5', {'W': 0x3c}, {'DATA:12': 0x3c}),
 ('tris_c', 'tris 7', {'W': 0x81}, {'DATA:14': 0x81}),
 ('option_is_a_hardware_op', 'dw 0x0062', {'W': 1}, {'PCODEOPS': 1}),
 # ---- indirect addressing
 ('movwi_preinc', 'movwi ++FSR0', {'FSR0': 0x100, 'W': 0xaa}, {'FSR0': 0x101, 'DATA:101': 0xaa, 'DATA:100': 0}),
 ('movwi_postinc', 'movwi FSR0++', {'FSR0': 0x120, 'W': 0xdd}, {'FSR0': 0x121, 'DATA:120': 0xdd}),
 ('movwi_predec', 'movwi --FSR0', {'FSR0': 0x120, 'W': 0xcc}, {'FSR0': 0x11f, 'DATA:11f': 0xcc}),
 ('movwi_postdec', 'movwi FSR1--', {'FSR1': 0x150, 'W': 0xbb}, {'FSR1': 0x14f, 'DATA:150': 0xbb}),
 ('moviw_preinc_zero', 'moviw ++FSR0', {'FSR0': 0x100, 'W': 5}, {'W': 0, 'FSR0': 0x101, 'Z': 1}),
 ('moviw_postinc', 'moviw FSR1++', {'FSR1': 0x150, 'DATA:150': 0x77, 'Z': 1}, {'W': 0x77, 'FSR1': 0x151, 'Z': 0}),
 ('moviw_indexed', 'moviw 5[FSR0]', {'FSR0': 0x100, 'DATA:105': 0x42}, {'W': 0x42, 'FSR0': 0x100, 'Z': 0}),
 ('movwi_indexed_neg', 'movwi -2[FSR1]', {'FSR1': 0x102, 'W': 0x12}, {'DATA:100': 0x12, 'FSR1': 0x102}),
 ('addfsr_neg', 'addfsr FSR1,-3', {'FSR1': 0x101}, {'FSR1': 0xfe}),
 ('addfsr_carry', 'addfsr FSR0,1', {'FSR0': 0xff}, {'FSR0': 0x100}),
 ('addfsr_wrap', 'addfsr FSR0,-1', {'FSR0': 0}, {'FSR0': 0xffff}),
 ('movwf_indf0', 'movwf 0', {'FSR0': 0x230, 'W': 0x5a}, {'DATA:230': 0x5a}),
 ('movf_indf1', 'movf 1,w', {'FSR1': 0x240, 'DATA:240': 0x33}, {'W': 0x33}),
 ('incf_indf0', 'incf 0,f', {'FSR0': 0x230, 'DATA:230': 9}, {'DATA:230': 10}),
 # ---- banking
 ('movlb_bank2', 'movlb 2\n movwf 0x20', {'W': 0x11}, {'BSR': 2, 'DATA:120': 0x11, 'DATA:20': 0}),
 ('movlb_bank63', 'movlb 0x3f\n movwf 0x20', {'W': 0x22}, {'BSR': 0x3f, 'DATA:1fa0': 0x22}),
 ('common_ram_any_bank', 'movlb 5\n movwf 0x70', {'W': 0x33}, {'DATA:70': 0x33, 'DATA:2f0': 0}),
 ('core_register_any_bank', 'movlb 3\n movwf 4', {'W': 0x12}, {'FSR0L': 0x12, 'FSR0': 0x12, 'DATA:184': 0}),
 ('bsr_is_6_bits', 'movwf 0x20', {'BSR': 0xc1, 'W': 0x44}, {'DATA:a0': 0x44}),
 # ---- control flow
 ('goto_default_page', 'goto 0x010', {}, {'PCnext': 0x10}, 0x10),
 ('goto_after_movlp_and_back', 'movlp 0x08\n movlp 0x00\n goto 0x010', {}, {'PCnext': 0x10}, 0x10),
 ('goto_forward', 'goto L1\n movlw 1\nL1: movlw 2', {}, {'W': 2}),
 ('goto_pclath_bit3', 'movlp 0x08\n goto 0x010', {}, {'PCnext': 0x810}, 0x810),
 ('goto_pclath_top', 'movlp 0x78\n goto 0x010', {}, {'PCnext': 0x7810}, 0x7810),
 ('goto_pclath_low_bits_ignored', 'movlp 0x07\n goto 0x010', {}, {'PCnext': 0x10}, 0x10),
 ('call_pushes_return_address', 'call sub\n nop\nsub: nop\n nop', {}, {'HWSTACK:0/2': 0x101, 'STKPTR': 1}, 0x103),
 ('call_pclath', 'movlp 0x10\n call 0x30', {}, {'HWSTACK:0/2': 0x102, 'PCnext': 0x1030, 'PCLATH': 0x10}, 0x1030),
 ('call_return', 'movlw 1\n call sub\n addlw 2\n---\nsub: addlw 0x10\n return', {}, {'W': 0x13, 'STKPTR': 0}),
 ('retlw', 'call sub\n---\nsub: retlw 0x42', {'W': 9}, {'W': 0x42, 'STKPTR': 0}),
 ('retfie_sets_gie', 'call sub\n---\nsub: retfie', {}, {'INTCON': 0x80, 'STKPTR': 0}),
 ('nested_calls', 'call suba\n nop\nsuba: call subb\n nop\nsubb: nop\n nop', {}, {'HWSTACK:0/2': 0x101, 'HWSTACK:1/2': 0x103, 'STKPTR': 2}, 0x105),
 ('callw', 'callw', {'PCLATH': 1, 'W': 0x20}, {'HWSTACK:0/2': 0x101, 'PCnext': 0x120}, 0x120),
 ('callw_pclath_high', 'callw', {'PCLATH': 0x7f, 'W': 0xff}, {'PCnext': 0x7fff}, 0x7fff),
 ('brw', 'brw\n movlw 1\n movlw 2\n movlw 3', {'W': 2}, {'W': 3}),
 ('bra_forward', 'bra L\n movlw 1\nL: movlw 2', {}, {'W': 2}),
 ('bra_backward', 'bra start2\nbody: movlw 7\n bra done\nstart2: bra body\ndone: nop', {}, {'W': 7}),
 ('computed_goto_addwf_pcl', 'movlw 2\n addwf 2,f\n movlw 1\n movlw 2\n movlw 3', {'PCLATH': 1}, {'W': 3}),
 ('movwf_pcl_page', 'movwf 2', {'PCLATH': 2, 'W': 0x10}, {'PCnext': 0x210}, 0x210),
 ('movwf_pcl_15bit', 'movwf 2', {'PCLATH': 0x7f, 'W': 0xff}, {'PCnext': 0x7fff}, 0x7fff),
 ('pcl_reads_next_address', 'movf 2,w', {}, {'W': 0x01}),
 ('movlp', 'movlp 0x7f', {}, {'PCLATH': 0x7f}),
]

def assemble(asm):
    """gpasm: returns (main_words, all_words) for the program at org 0x100. A line "---" marks the
    end of the part that runs; its address comes from the label __end__ in the listing."""
    text = asm.replace('---', '__end__:\n\torg 0x180') if '---' in asm else asm + '\n__end__:'
    src = '\tprocessor p16f15386\nFSR0\tequ 0\nFSR1\tequ 1\n\torg 0x100\n' + '\n'.join(
        l if l[:1] not in ' \t' and ':' in l else '\t' + l.strip() for l in text.split('\n')) + '\n\tend\n'
    with tempfile.TemporaryDirectory() as d:
        open(d + '/a.asm', 'w').write(src)
        r = subprocess.run(['gpasm', '-o', d + '/a.hex', d + '/a.asm'],
                           capture_output=True, text=True)
        if r.returncode:
            raise SystemExit('gpasm failed for %r:\n%s' % (asm, r.stdout + r.stderr))
        words = {}
        for l in open(d + '/a.hex'):
            l = l.strip()
            if not l.startswith(':') or l[7:9] != '00':
                continue
            n = int(l[1:3], 16); a = int(l[3:7], 16)
            data = bytes.fromhex(l[9:9 + 2 * n])
            for i in range(0, n, 2):
                words[(a + i) // 2] = data[i] | data[i + 1] << 8
        m = re.search(r'^__end__\s+ADDRESS\s+([0-9A-Fa-f]+)', open(d + '/a.lst').read(), re.M | re.I)
        endaddr = int(m.group(1), 16)
    allw = [words.get(i, 0) for i in range(0x100, max(words) + 1)]
    return endaddr - 0x100, allw

def fmt(v):
    return hex(v)

def render(cases, broken=False):
    out = ['# generated by test/emu/cases.py; do not edit']
    for i, c in enumerate(cases):
        name, asm, st, ex = c[:4]
        end = c[4] if len(c) > 4 else None
        mainw, words = assemble(asm) if not broken else (None, None)
        out.append('case ' + name)
        out.append('#   ' + asm.replace('\n', ' ; '))
        out.append('code ' + ' '.join('%04x' % w for w in words))
        if end is not None:
            out.append('end %x' % end)
        elif '---' in asm:
            out.append('main %d' % mainw)
        for k, v in st.items():
            out.append('set %s %s' % (k, fmt(v)))
        for k, v in ex.items():
            out.append('expect %s %s' % (k, fmt(v)))
        out.append('end')
    return '\n'.join(out) + '\n'

if __name__ == '__main__':
    here = os.path.dirname(os.path.abspath(__file__))
    if '--assemble' in sys.argv:
        open(here + '/cases.txt', 'w').write(render(CASES))
    elif '--broken' in sys.argv:
        # keep cases.txt, but make the first expectation of the first case wrong
        txt = open(here + '/cases.txt').read().split('\n')
        for i, l in enumerate(txt):
            if l.startswith('expect '):
                p = l.split()
                txt[i] = 'expect %s %s' % (p[1], hex(int(p[2], 0) ^ 1))
                break
        sys.stdout.write('\n'.join(txt))
    else:
        sys.stdout.write(open(here + '/cases.txt').read())
