# PIC16F153xx for Ghidra

SLEIGH processor module for the Microchip **PIC16(L)F153xx** families (enhanced mid-range core with
a 15-bit program counter, a 6-bit bank select register and 16-level hardware stack: PIC16F15313,
15323, 15324, 15325, 15344, 15345, 15354, 15355, 15356, 15375, 15376, 15385, 15386, ...). Language
ID `PIC-16:LE:16:PIC-16F153xx`.

Original work by Michael Huebler (`@mh-`), proposed to Ghidra as
[pull request #667](https://github.com/NationalSecurityAgency/ghidra/pull/667) (Apache-2.0). This
fork keeps the PR's commit and adds the Ghidra-Rare verification and fixes; see `CREDITS.md` for who
did what and `GHIDRA-RARE.md` for the test results, the known gaps and the reference-tool notes.

## Install

Download the zip for your Ghidra version from the fork's [Releases page](https://github.com/aleph-void/ghidra-pic16f153xx/releases) (built for Ghidra
12.1.3, 12.1.4 and 12.2) and use *File > Install Extensions*, or copy the directory to
`<ghidra>/Ghidra/Extensions/`. The module can be installed next to Ghidra's own PIC modules: its
language ID differs from the official `PIC-16` and `PIC-16F` languages.

Intel hex files (what MPLAB X and gpasm produce) load with Ghidra's *Intel Hex* loader: choose the
language `PIC-16:LE:16:PIC-16F153xx`. Hex addresses count bytes, two per 14-bit instruction word,
so the CODE space shows word addresses.

## Relation to Ghidra's PIC-16F module

The official `PIC-16F` language (enhanced mid-range) differs from the 153xx parts in the width of
`BSR`/`MOVLB` (5 against 6 bits), the program counter (13 against 15 bits), the data memory map and
the SFR addresses. The PR therefore added a separate language, and so does this fork. It would be
possible to fold it into the official module as a variant (a `PIC16F153XX` define in
`pic16f.sinc`, as the PR discussion suggested); this fork keeps it separate so that it builds with
no change to the official module.

## What the module covers

All 49 instructions of the PIC16(L)F15325/45 data sheet, the legacy `OPTION` and `TRIS`, the
`BC/BNC/BZ/BNZ/SKPC/SKPNC/SKPZ/SKPNZ` assembler pseudo-instructions (off by default: set the
context bit `doPseudo`), SFR labels from the data sheet, PCLATH-aware `CALL`/`GOTO`, computed `GOTO`
and `CALLW`, `BRA`/`BRW`, skip instructions, indirect addressing (`INDFn`, `MOVIW`/`MOVWI`,
`ADDFSR`) and the hardware return stack.

## Known limitations of the original, and what became of them

The PR had no README. These are the problems found in the PR, its discussion and Ghidra's issue
tracker:

| Limitation | Status |
|---|---|
| `LSLF`, `LSRF`, `ASRF` missing, `RETLW` matched their opcodes (Ghidra #1362) | fixed |
| Skip instructions decompile wrongly (`BTFSC`/`BTFSS` chains, Ghidra #7325) | fixed: skips branch to `inst_next2` |
| Hard-coded `PCLATH` values (reviewer's concern), wrong above 16K words; `CALL`/`GOTO` decompiled as jump tables | fixed: `MOVLP` sets a disassembly context (`pcHi`), so `CALL`/`GOTO` are direct branches; per-page start values in the pspec |
| Wrong INTCON bit names, 32 wrong or misspelled SFR symbols | fixed: generated from the data sheet |
| `SKPC`/`SKPNC`/`SKPZ`/`SKPNZ` had BTFSC and BTFSS swapped | fixed |
| Flags: `RLF`/`RRF`/`MOVIW` Z, digit-carry polarity of the subtractions, `SUBWFB` | fixed |
| `CALL`, `GOTO`, `BRA`, `BRW`, `CALLW`, returns: wrong p-code | fixed |
| Language shares the name `pic16.ldefs` with Ghidra's | fixed: `pic16f153xx.ldefs` |
| Linear data memory (FSR 0x2000-0x2FEF) and program-flash window (FSR 0x8000+) | remaining, see GHIDRA-RARE.md |
| `STKPTR`/`TOSL`/`TOSH`, stack overflow/underflow, shadow registers | remaining (hardware state) |
| SFR names only for the PIC16(L)F15325/45 | remaining (other family members differ) |
| Ghidra #1555 (Intel hex addresses) | not a bug: hex addresses are bytes |
