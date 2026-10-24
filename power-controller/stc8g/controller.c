/* SPDX-License-Identifier: GPL-3.0-or-later
 * New implementation of the interface described by atar-axis/tc1-u4.
 * See README.md for differences and hardware verification requirements.
 */
#include "controller.h"

void pc_init(volatile PowerController *p)
{
    p->state = PC_OFF;
    p->button_history = 0xff;
    p->button_level = 1;
    p->online_history = 0;
    p->online_level = 0;
    p->elapsed = 0;
    p->boost = 0;
    p->avr_button = 0;
}

void pc_tick(volatile PowerController *p, uint8_t button, uint8_t online)
{
    /* Retain the previous level until eight consecutive samples agree. */
    p->button_history = (uint8_t)((p->button_history << 1) | !!button);
    if (p->button_history == 0) p->button_level = 0;
    else if (p->button_history == 0xff) p->button_level = 1;

    /* Reject single-sample glitches on the AVR's acknowledgment output. */
    p->online_history = (uint8_t)(((p->online_history << 1) | !!online) & 3);
    if (p->online_history == 0) p->online_level = 0;
    else if (p->online_history == 3) p->online_level = 1;

    switch (p->state) {
    case PC_OFF:
        if (p->button_level == 0) {
            p->elapsed = 0;
            p->state = PC_BOOT;
        }
        break;
    case PC_BOOT:
        p->elapsed++;
        if (p->online_level) {
            p->state = PC_ONLINE;
        } else if (p->elapsed >= PC_BOOT_TICKS) {
            p->state = PC_WAIT_RELEASE;
        }
        break;
    case PC_ONLINE:
        if (p->online_level == 0) {
            p->elapsed = 0;
            p->state = PC_SHUTDOWN;
        }
        break;
    case PC_SHUTDOWN:
        /* Allow the AVR to finish showing its goodbye message. */
        p->elapsed++;
        if (p->elapsed >= PC_SHUTDOWN_TICKS) p->state = PC_WAIT_RELEASE;
        break;
    case PC_WAIT_RELEASE:
        /* Holding the key after timeout/shutdown must not restart power. */
        if (p->button_level) p->state = PC_OFF;
        break;
    default:
        p->state = PC_WAIT_RELEASE;
        break;
    }

    p->boost = (p->state == PC_BOOT || p->state == PC_ONLINE ||
                p->state == PC_SHUTDOWN);
    /* Keep the AVR signal low while unpowered to avoid backfeeding it. */
    p->avr_button = p->boost ? p->button_level : 0;
}
