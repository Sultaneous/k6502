# k6502
*MOS 6502 Python-based utilities, including disassembler, assembler, and more in-class libraries.*

## DOCUMENTATION STATUS
Documentation coming soon.  
* Prototype:  Complete
* Code Review and Refactoring: Underway
* Tagged Commit: Pending
* Documentation: Pending

## URGENT REQUESTS
If you need some information about the K6502 project urgently, prior to the
documentation complete stage, please contact me directly through github.

## KDis6502 ISSUES ##
* KDis6502 currently doesn't handle illegal opcodes.  I plan on adding that support next, with a command line switch to enable.  My first few tests in the wild ran into illegal opcodes, causing the utility to error out.
* Sometimes, they are not necessarily illegal opcodes, but data definitions.  Consider the following:

```Assembly
   *= $C000
   
   JMP code
init:
   Alias .byte $0B,0,0,0,0,0,0,0
   Struct .byte 0,0,0,0,0,0,0,0,0,0

code:
   LDA #$01
   STA $0400
   ...
```

In the above case, the following is happening:
* The location header (2 bytes) is $C000
* THe initial instruction is a Jump to the code segment, jumping over the data segment
* The data segment is oddly enough at the top of the program.  This is valid, but non-standard.  6502 does not use code/data segments, allowing tricks like self-modifying code and the one seen above, so it's up to the programmer.
* 'Alias' and 'Struct' reserve a total of 18 bytes;
* The 6592 implements this not with an ASM command, but by just resrving space in memory (in this case, at $C002 to $C014)
* The first byte reserved has a value of $0B -> the disassembler tries to decode this, not knowing it is data.  But $0B is not a valid opcode control byte - it is an illegal one.  So the disassembler errors out.
* One solution is for the disassembler to just dump unknonwn control bytes verbatim, and assume they are all implied addressing (no extra addressing bytes).  But this doesn't always work; consider the $00 bytes in the data.  These equate to a valid instruction; BRK.
