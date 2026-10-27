# Ghidra-Rare notes: PIC16F153xx

Verification of the PIC16F153xx module (Ghidra pull request #667) to the Ghidra-Rare bar
([docs/VERIFICATION.md](https://github.com/aleph-void/Ghidra-Rare/blob/main/docs/VERIFICATION.md)).
Credits and the list of changes are in `CREDITS.md`; the original authors' README text is kept
in `README.md`.

- Language ID: `PIC-16:LE:16:PIC-16F153xx` (processor `PIC-16`, variant `PIC-16F153XX`). It does not
  collide with Ghidra's `PIC-16:LE:16:PIC-16` and `PIC-16:LE:16:PIC-16F`.
- Built and tested with Ghidra 12.1.3, 12.1.4 and 12.2 (`tools/build-module.sh --standard`).
- `pic16f153xx.sla` is about 9 KB.

## Running the tests

```
GHIDRA_INSTALL_DIR=<ghidra with this directory in Ghidra/Processors/PIC16F153xx> test/run-tests.sh [--real <workdir>] [outdir]
```

Needs `gpasm`/`gpdasm` (gputils 1.5.x) and `unidasm` (MAME tools) on `PATH` (steps are skipped when
a tool is missing); `--real` also downloads two small hex files (pinned URL and SHA-256). Python 3
and `pdftotext` are needed to regenerate the pspec from the data sheet (`test/fetch-datasheet.sh`,
`test/gen_pspec.py`); the data sheet is never committed.

## Results

| Area | Result |
|---|---|
| Decode | All 16384 14-bit instruction words (the whole instruction set: no sampling needed) against gpdasm (gputils 1.5.2, device p16f15386): 16384 slots, 156 both-invalid, 0 unexplained, 4 explained (3 CLRW encodings with the data sheet's `x` bits not `11`, which gpdasm rejects; `0x0061`, which gpdasm decodes as an ICD `halt` that is not in the 15325/45 instruction set). Against MAME `unidasm -arch pic16c62x` for the 14080 encodings the classic and the enhanced core share: 0 unexplained, 90 explained (enhanced-core instructions MAME's classic core does not know). The 8 assembler pseudo-instructions (`doPseudo=1`) against gpasm's encodings: 8/8. `CALL`/`GOTO` targets with `pcHi` set: checked. Both sides are normalised to numbers before comparing (register names, `w`/`f`, `#`), so "exact" and "semantic" agreement are not reported separately. `reached/total`: **118/118** constructors (two seeds). |
| Semantics | 112 emulator cases (`test/emu/cases.txt`): the machine code is assembled with gpasm, the expected registers, flags and memory were worked out by hand from the data sheet (every ALU instruction with carry, digit carry, zero, borrow polarity, STATUS as destination, shifts through carry, all four skip instructions and chained skips, every MOVIW/MOVWI/ADDFSR mode, INDF0/INDF1, banking with a 6-bit BSR, common RAM, core registers from every bank, GOTO/CALL with MOVLP, CALLW, BRW, BRA, RETURN/RETLW/RETFIE, nested calls and the return stack, computed GOTO, 15-bit PCL jumps). A copy with one wrong expectation reports exactly that case ("broken expectation detected"). In addition 6 runs of `test/real/algos.asm` (CRC-16/CCITT, 16x16 multiply, XTEA, bubble sort through FSR, computed-goto table; 360 instructions) match results computed in Python. |
| Real code | Third-party: the MIT-licensed PIC16F15344/5 bootloader stubs of react66/bootloader-pic16 (pinned commit, SHA-256 checked), and `test/real/algos.asm`. Intel hex import with Ghidra's own loader, auto-analysis: 430 instructions and 19 functions for each stub (the 10 undefined bytes are the configuration words), 360 instructions and 9 functions for `algos`; 0 bad-instruction bookmarks, 0 error bookmarks, 0 decompile failures; disassembly equals gpdasm at every address (430/430, 430/430, 360/360). The decompiled CRC-16 is the algorithm. |
| Spec files | `pic16f153xx.cspec` with `<global>` ranges (GPR of 50 banks, the 15-bit code space), `pic16f153xx.pspec` generated from the data sheet's register summary (263 SFR symbols, volatile ranges, `Reset`/`Interrupt` entry points), no ELF/DWARF files (see Unverified). |

### Doesn't work

- **Linear data memory and the program-flash window.** `FSR` values `0x2000-0x2FEF` address the
  80-byte GPR blocks of all banks as one linear array, and values `0x8000-0xFFFF` read the low byte
  of program flash through `INDFn`/`MOVIW`. The module treats these as ordinary `DATA` addresses.
  A `DATA` space cannot alias another space, and an operand constructor can export only one
  varnode, so modelling them means a divide-by-80 or a conditional on every `INDF` access; the
  decompiler output of every pointer access would turn into that arithmetic. Compiled code that uses
  linear addressing therefore shows distinct variables for the linear and banked views of the same
  RAM.
- **`TOSL`/`TOSH`/`STKPTR` SFRs, stack overflow/underflow, 16-level wrap-around.** The return stack is
  an abstract space; its depth is not limited and the registers are only labels (hardware state).
- **`CLRWDT`, `SLEEP`, `RESET`, `OPTION`** are pcodeops (hardware); `CLRWDT`/`SLEEP` set TO/PD.
- **Interrupt entry** (automatic context save into the shadow registers, GIE clear) is not modelled
  (hardware behaviour of the interrupt controller, no instruction).
- **`PCLATH` written by anything but `MOVLP`** (`MOVWF PCLATH`, `ADDWF PCLATH`, ...) is not followed
  by the `pcHi` context that decides the target of `CALL`/`GOTO`; XC8 and gpasm use `MOVLP`. A
  `GOTO`/`CALL` target is the page set by the last `MOVLP` on the path in which the instruction was
  first disassembled (hardware uses the value of `PCLATH` at run time).
- STATUS: `TO` and `PD` are writable in the model (read-only in silicon) for the instructions that do
  not affect Z/DC/C (`MOVWF STATUS`, `BCF/BSF STATUS`, `SWAPF STATUS`).
- SFR names and addresses are those of the PIC16(L)F15325/45; other family members share most but
  not all of them (peripherals differ).
- The assembler pseudo-instructions `CLRC`, `SETC`, `CLRZ`, ... `SKPDC`, `BDC` are not decoded (they
  are ordinary `BCF/BSF/BTFSC/BTFSS` words, which is how they are disassembled); the PR already
  covered only `BC/BNC/BZ/BNZ/SKPC/SKPNC/SKPZ/SKPNZ`.

### Unverified

- No Microchip XC8 or MPLAB-built firmware for a 153xx part was available under a free license, so
  XC8's calling convention (the cspec passes the first byte argument and the result in `W`), its
  DWARF output and its ELF files (no opinion or `.dwarf` file is shipped) are untested.
- Real silicon behaviour (the module follows the data sheet; the data sheet's instruction table has
  a garbled MOVLB line, resolved from the text, the PR thread and gputils: `0x0140 | k6`).
- Other family members (PIC16F15313/15323/15324/15354/15355/15356/15375/15376/15385/15386): the
  instruction set is shared, the memory sizes and SFR maps are not.
- The upper two bits of the 16-bit cell (bits 14-15) are ignored by the decoder.

### Reference tool notes

- gpdasm prints `addfsr` with the address of `FSRnL` (4 or 6) instead of `n` (display only).
- gpdasm accepts only `0x0103` as CLRW and decodes `0x0061` as `halt`.
- gpdasm's `-c` option does not turn the pseudo-instruction pairs back into `bc`/`bz`...
- The data sheet DS40001865D lists `00 000 0k kkkk` for MOVLB, which is not a 14-bit pattern; the
  instruction is `00 0001 01kk kkkk` (gputils, PR author's report on the Microchip forum).
- MAME's PIC16C62x disassembler knows only the classic instruction set.
