; Test program for the Ghidra-Rare PIC16F153xx module (written for Ghidra-Rare, MIT/Apache-2.0
; like the rest of the tests). Four routines that exercise the enhanced mid-range core the way
; compiled code does: a bitwise CRC-16 (shifts through carry, FSR post-increment), a 16x16->32
; multiply (add-with-carry chains), XTEA with 32-bit helper macros (indexed FSR loads, carry
; chains), a bubble sort through INDF/FSR (SUBWF carry), and a computed-goto table (ADDWF PCL).
; gpasm builds it; the expected results are computed in algos.py.
	processor p16f15386
FSR0	equ 0
FSR1	equ 1
PCL	equ 2
STATUS	equ 3
FSR0L	equ 4
FSR0H	equ 5
FSR1L	equ 6
FSR1H	equ 7
	radix dec

; ---- data (bank 0 GPR and common RAM)
V0	equ 0x20	; XTEA v0 (4 bytes, little endian)
V1	equ 0x24
KEY	equ 0x28	; 16 bytes
SUM	equ 0x38
T1	equ 0x3c
T2	equ 0x40
BUF	equ 0x50	; 16 bytes: CRC input, then the bytes to sort
MA	equ 0x60	; multiplicand (32 bit working copy)
MB	equ 0x64	; multiplier 16 bit
MR	equ 0x66	; product 32 bit
CRCH	equ 0x70
CRCL	equ 0x71
CNT	equ 0x72
BITC	equ 0x73
RND	equ 0x74
IDX	equ 0x75
SORTN	equ 0x76
SWAPPED	equ 0x77
NIB	equ 0x78	; hex digit in, ASCII out
CMP	equ 0x79
SWT	equ 0x7a

; ---- 32-bit macros on named variables
COPY32	macro d,s
	movf s,w
	movwf d
	movf s+1,w
	movwf d+1
	movf s+2,w
	movwf d+2
	movf s+3,w
	movwf d+3
	endm
ADD32	macro d,s
	movf s,w
	addwf d,f
	movf s+1,w
	addwfc d+1,f
	movf s+2,w
	addwfc d+2,f
	movf s+3,w
	addwfc d+3,f
	endm
XOR32	macro d,s
	movf s,w
	xorwf d,f
	movf s+1,w
	xorwf d+1,f
	movf s+2,w
	xorwf d+2,f
	movf s+3,w
	xorwf d+3,f
	endm
SHL1	macro x
	lslf x,f
	rlf x+1,f
	rlf x+2,f
	rlf x+3,f
	endm
SHR1	macro x
	lsrf x+3,f
	rrf x+2,f
	rrf x+1,f
	rrf x,f
	endm
; T = v ^ ... : t1 = ((v << 4) ^ (v >> 5)) + v
MIX	macro v
	COPY32 T1,v
	SHL1 T1
	SHL1 T1
	SHL1 T1
	SHL1 T1
	COPY32 T2,v
	SHR1 T2
	SHR1 T2
	SHR1 T2
	SHR1 T2
	SHR1 T2
	XOR32 T1,T2
	ADD32 T1,v
	endm
; T2 = key[idx] where IDX holds 0..3
LOADKEY	macro
	movf IDX,w
	andlw 3
	movwf IDX
	lslf IDX,f
	lslf IDX,w
	addlw KEY
	movwf FSR0L
	clrf FSR0H
	moviw FSR0++
	movwf T2
	moviw FSR0++
	movwf T2+1
	moviw FSR0++
	movwf T2+2
	moviw FSR0++
	movwf T2+3
	endm

	org 0
	goto start
	org 4
	retfie
	org 0x100
start:
	call crc16
	call mul16
	call xtea
	call sort
	call hexdigit
done:
	nop
	goto done

; CRC-16/CCITT-FALSE over BUF[0..15]; result in CRCH:CRCL
crc16:
	movlw 0xff
	movwf CRCH
	movwf CRCL
	movlw low BUF
	movwf FSR0L
	clrf FSR0H
	movlw 16
	movwf CNT
crc_byte:
	moviw FSR0++
	xorwf CRCH,f
	movlw 8
	movwf BITC
crc_bit:
	lslf CRCL,f
	rlf CRCH,f
	btfss STATUS,0
	goto crc_next
	movlw 0x10
	xorwf CRCH,f
	movlw 0x21
	xorwf CRCL,f
crc_next:
	decfsz BITC,f
	goto crc_bit
	decfsz CNT,f
	goto crc_byte
	return

; MR = MA(16 bit, at MA,MA+1) * MB(16 bit); MA+2,MA+3 are the shifted-out high bytes
mul16:
	clrf MA+2
	clrf MA+3
	clrf MR
	clrf MR+1
	clrf MR+2
	clrf MR+3
	movlw 16
	movwf CNT
mul_loop:
	lsrf MB+1,f		; shift the multiplier right, low bit into carry
	rrf MB,f
	btfss STATUS,0
	goto mul_skip
	ADD32 MR,MA
mul_skip:
	SHL1 MA
	decfsz CNT,f
	goto mul_loop
	return

; XTEA encrypt (V0,V1) with KEY, 32 rounds
xtea:
	clrf SUM
	clrf SUM+1
	clrf SUM+2
	clrf SUM+3
	movlw 32
	movwf RND
xtea_round:
	MIX V1
	movf SUM,w
	movwf IDX
	LOADKEY
	ADD32 T2,SUM
	XOR32 T1,T2
	ADD32 V0,T1
	movlw 0xb9		; sum += 0x9e3779b9
	addwf SUM,f
	movlw 0x79
	addwfc SUM+1,f
	movlw 0x37
	addwfc SUM+2,f
	movlw 0x9e
	addwfc SUM+3,f
	MIX V0
	movf SUM+1,w
	movwf IDX
	lsrf IDX,f
	lsrf IDX,f
	lsrf IDX,f
	LOADKEY
	ADD32 T2,SUM
	XOR32 T1,T2
	ADD32 V1,T1
	decfsz RND,f
	goto xtea_round
	return

; bubble sort BUF[0..15] ascending (unsigned), through FSR0/FSR1
sort:
	movlw 15
	movwf SORTN
sort_pass:
	clrf SWAPPED
	movlw low BUF
	movwf FSR0L
	clrf FSR0H
	movlw low (BUF+1)
	movwf FSR1L
	clrf FSR1H
	movf SORTN,w
	movwf CNT
sort_cmp:
	moviw 0[FSR1]		; W = right
	movwf CMP
	moviw 0[FSR0]		; W = left
	subwf CMP,w		; W = right - left, C = 1 when right >= left
	btfsc STATUS,0
	goto sort_noswap
	moviw 0[FSR0]		; swap
	movwf SWT
	moviw 0[FSR1]
	movwi 0[FSR0]
	movf SWT,w
	movwi 0[FSR1]
	movlw 1
	movwf SWAPPED
sort_noswap:
	addfsr FSR0,1
	addfsr FSR1,1
	decfsz CNT,f
	goto sort_cmp
	movf SWAPPED,f
	btfsc STATUS,2		; Z set: no swap in this pass
	return
	decfsz SORTN,f
	goto sort_pass
	return

; NIB (0..15) -> ASCII hex digit in NIB, with a computed-goto table of RETLWs
hexdigit:
	movlp (hextab>>8) & 0x7f
	movf NIB,w
	andlw 0x0f
	call hextab
	movwf NIB
	movlp 0
	return
	org 0x600
hextab:
	addwf PCL,f
	retlw '0'
	retlw '1'
	retlw '2'
	retlw '3'
	retlw '4'
	retlw '5'
	retlw '6'
	retlw '7'
	retlw '8'
	retlw '9'
	retlw 'A'
	retlw 'B'
	retlw 'C'
	retlw 'D'
	retlw 'E'
	retlw 'F'
	end
