   *= $C000

   lda #1
   ldx #0
rep:
   sta $0400, x
   inx 
   bne rep
   rts 