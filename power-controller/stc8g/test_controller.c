/* SPDX-License-Identifier: GPL-3.0-or-later */
#include <assert.h>
#include <stdio.h>
#include "controller.h"

static PowerController p;
static void ticks(unsigned n, uint8_t button, uint8_t online)
{
    while (n--) pc_tick(&p, button, online);
}
static void boot(void)
{
    pc_init(&p);
    ticks(PC_DEBOUNCE_TICKS, 0, 0);
    assert(p.state == PC_BOOT && p.boost && !p.avr_button);
    ticks(2, 0, 1);
    assert(p.state == PC_ONLINE);
    ticks(PC_DEBOUNCE_TICKS, 1, 1);
    assert(p.avr_button && p.boost);
}
int main(void)
{
    pc_init(&p);
    ticks(1000, 1, 0);
    assert(p.state == PC_OFF && !p.boost && !p.avr_button);
    /* A bouncing button must not turn the converter on. */
    for (unsigned i=0; i<40; i++) pc_tick(&p, i & 1, 0);
    assert(p.state == PC_OFF && !p.boost);
    ticks(PC_DEBOUNCE_TICKS-1, 0, 0);
    assert(!p.boost);
    ticks(1, 0, 0);
    assert(p.state == PC_BOOT && p.boost);
    ticks(PC_BOOT_TICKS-1, 0, 0);
    assert(p.boost);
    ticks(1, 0, 0);
    assert(!p.boost && p.state == PC_WAIT_RELEASE);
    ticks(1000, 0, 0);
    assert(!p.boost);  /* no boot loop while held after failed startup */
    ticks(PC_DEBOUNCE_TICKS, 1, 0);
    assert(p.state == PC_OFF);

    boot();
    /* Normal short press and release, after debounce. */
    ticks(PC_DEBOUNCE_TICKS-1, 0, 1);
    assert(p.avr_button);
    ticks(1, 0, 1);
    assert(!p.avr_button && p.boost);
    ticks(PC_DEBOUNCE_TICKS, 1, 1);
    assert(p.avr_button && p.boost);
    /* Single-sample acknowledgment glitches do not remove power. */
    ticks(1, 1, 0);
    ticks(2, 1, 1);
    assert(p.state == PC_ONLINE);
    /* A long press is forwarded, with no independent shutdown timer. */
    ticks(1000, 0, 1);
    assert(p.state == PC_ONLINE && p.boost && !p.avr_button);
    /* AVR drops PD2: 10 ms input filter, then 500 ms goodbye interval. */
    ticks(2, 0, 0);
    assert(p.state == PC_SHUTDOWN && p.boost);
    ticks(PC_SHUTDOWN_TICKS-1, 0, 0);
    assert(p.boost);
    ticks(1, 0, 0);
    assert(p.state == PC_WAIT_RELEASE && !p.boost && !p.avr_button);
    ticks(1000, 0, 0);
    assert(!p.boost);
    ticks(PC_DEBOUNCE_TICKS, 1, 0);
    assert(p.state == PC_OFF);
    ticks(PC_DEBOUNCE_TICKS, 0, 0);
    assert(p.state == PC_BOOT && p.boost); /* can restart after release */
    p.state = 255;
    ticks(1, 0, 0);
    assert(!p.boost && p.state == PC_WAIT_RELEASE);
    /* Startup must also work after prolonged powered standby. On hardware,
     * R2 keeps Timer0 active in IDLE so these samples continue arriving.
     */
    pc_init(&p);
    ticks(10000, 1, 0);
    assert(p.state == PC_OFF && !p.boost);
    ticks(PC_DEBOUNCE_TICKS, 0, 0);
    assert(p.state == PC_BOOT && p.boost && !p.avr_button);
    puts("Power controller: debounce, startup, forwarding, timeout, shutdown and restart passed.");
    return 0;
}
