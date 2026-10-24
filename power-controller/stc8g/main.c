/* SPDX-License-Identifier: GPL-3.0-or-later
 * Experimental blue-PCB T7 STC8G1K08(A), SOP8. Not an STC15 binary.
 * Register definitions checked against STC8G-en.pdf, chapters 6, 9, 11, 12.
 */
#include <8051.h>
#include "controller.h"

__sfr __at (0x8e) AUXR;
__sfr __at (0x8f) INTCLKO;
__sfr __at (0xb1) P3M1;
__sfr __at (0xb2) P3M0;
__sfr __at (0xc1) WDT_CONTR;
__sfr __at (0xc8) P5;
__sfr __at (0xc9) P5M1;
__sfr __at (0xca) P5M0;
__sfr __at (0xef) AUXINTIF;

__sbit __at (0xcc) BUTTON;      /* P5.4, SOP8 pin 1, low when pressed */
__sbit __at (0xcd) BOOST;       /* P5.5, SOP8 pin 3, high enables converter */
__sbit __at (0xb2) AVR_BUTTON;  /* P3.2, SOP8 pin 7 -> AVR PD1 */
__sbit __at (0xb3) AVR_ONLINE;  /* P3.3, SOP8 pin 8 <- AVR PD2 */

/* Program the effective CPU clock to 12 MHz with stcgal -t 12000.
 * Preserve the bootloader's calibrated oscillator AND clock divider.
 */
#define TIMER_RELOAD (65536UL - 5000UL)
static volatile PowerController controller;
#ifndef T7_IDLE_STANDBY
static volatile uint8_t sleep_ready;
#endif

static void timer_restart(void)
{
    TR0 = 0;
    TH0 = (uint8_t)(TIMER_RELOAD >> 8);
    TL0 = (uint8_t)TIMER_RELOAD;
    TF0 = 0;
    TR0 = 1;
}

void timer0_isr(void) __interrupt (1)
{
    /* Mode 0 reloads automatically: 12 MHz / 12 / 5000 = 200 Hz. */
    pc_tick(&controller, BUTTON, AVR_ONLINE);
    if (controller.boost) {
        BOOST = 1;
        AVR_BUTTON = controller.avr_button;
    } else {
        AVR_BUTTON = 0;
        BOOST = 0;
    }
#ifndef T7_IDLE_STANDBY
    sleep_ready = (controller.state == PC_OFF &&
                   controller.button_history == 0xff);
#endif
}

#ifndef T7_IDLE_STANDBY
void int2_isr(void) __interrupt (10)
{
    AUXINTIF &= (uint8_t)~0x10;
}

static void standby(void)
{
    EA = 0;
    if (!sleep_ready) { EA = 1; return; }
    TR0 = 0;
    /* Do not leave a pending timer interrupt competing with the wake edge. */
    ET0 = 0;
    TF0 = 0;
    AUXINTIF &= (uint8_t)~0x10;
    INTCLKO |= 0x10;
    if (BUTTON) {
        __asm
            setb _EA
            orl _PCON, #0x02
            nop
        __endasm;
    }
    EA = 0;
    INTCLKO &= (uint8_t)~0x10;
    /* Consume the old request before restarting Timer0. R1 left it set,
     * causing main to re-enter standby and reset the counter repeatedly
     * before the first 5 ms button sample. Clear it even if STOP was
     * skipped because the button was already low.
     */
    sleep_ready = 0;
    timer_restart();
    ET0 = 1;
    EA = 1;
}
#endif

void main(void)
{
    EA = 0;
    WDT_CONTR = 0;
    /* stcgal may select an oscillator/divider pair to obtain 12 MHz.
     * Do not overwrite CLKDIV (extended address FE01) or clock selection.
     */
    /* Set output latches low before enabling push-pull mode. Leave UART
     * pins P3.0/P3.1 untouched so the bootloader/programming path is free.
     */
    BOOST = 0;
    AVR_BUTTON = 0;
    BUTTON = 1;
    AVR_ONLINE = 1;
    P5M1 &= (uint8_t)~0x30;
    P5M0 = (P5M0 & (uint8_t)~0x10) | 0x20;
    P3M1 &= (uint8_t)~0x0c;
    P3M0 = (P3M0 & (uint8_t)~0x08) | 0x04;
    /* Inputs are quasi-bidirectional (weak pull-ups), as in the reference. */
    INTCLKO = 0;              /* no clock outputs or external interrupts yet */
    AUXR &= (uint8_t)~0x80;   /* Timer0 12T */
    TMOD &= 0xf0;             /* Timer0 mode 0, internal clock, no gating */
    pc_init(&controller);
#ifndef T7_IDLE_STANDBY
    sleep_ready = 0;
#endif
    timer_restart();
    ET0 = 1;
    EA = 1;
    for (;;) {
#ifndef T7_IDLE_STANDBY
        if (sleep_ready) standby();
        else
#endif
            PCON |= 0x01;     /* IDLE until next timer tick */
    }
}
