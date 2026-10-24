/* SPDX-License-Identifier: GPL-3.0-or-later */
#ifndef T7_CONTROLLER_H
#define T7_CONTROLLER_H
#include <stdint.h>

/* Hardware-independent counterpart of the atar-axis/tc1-u4 interface.
 * Call exactly once per 5 ms. Input/output values are electrical levels.
 */
enum { PC_OFF, PC_BOOT, PC_ONLINE, PC_SHUTDOWN, PC_WAIT_RELEASE };
enum { PC_DEBOUNCE_TICKS = 8, PC_BOOT_TICKS = 200, PC_SHUTDOWN_TICKS = 100 };
typedef struct {
    uint8_t state;
    uint8_t button_history;
    uint8_t button_level;
    uint8_t online_history;
    uint8_t online_level;
    uint16_t elapsed;
    uint8_t boost;
    uint8_t avr_button;
} PowerController;

void pc_init(volatile PowerController *p);
void pc_tick(volatile PowerController *p, uint8_t button, uint8_t online);
#endif
