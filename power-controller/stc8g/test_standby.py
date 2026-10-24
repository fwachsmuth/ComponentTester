"""Replay R1 timer starvation using the actual driver C with mocked SFRs.

Entering STOP is simulated as a button edge/INT2. This tests control flow;
it cannot establish whether the physical STC accepts that wake interrupt.
"""
from pathlib import Path
import re
import subprocess
import tempfile

driver = Path('main.c').read_text()
driver = driver.replace('#include <8051.h>', '''#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
static uint8_t EA, TR0, TH0, TL0, TF0, ET0, PCON, TMOD;
static unsigned stops;
static void simulated_stop(void);
#define __xdata
''')
driver = re.sub(r'__s(?:fr|bit)\s+__at\s*\(0x[0-9a-f]+\)\s+(\w+);',
                r'uint8_t \1;', driver)
driver = re.sub(r'\s+__interrupt\s*\(\d+\)', '', driver)
driver = re.sub(r'__asm\b.*?__endasm;', 'simulated_stop();', driver, flags=re.S)
driver = driver.replace('void main(void)', 'void unused_target_main(void)')
test = r'''
static unsigned samples;
static uint8_t auto_ack;
static void simulated_stop(void) {
    /* Timer0 must be stopped/masked while INT2 is the wake source. */
    if (TR0 || ET0 || TF0 || !(INTCLKO & 0x10)) {
        puts("Invalid STOP entry interrupt state");
        exit(5);
    }
    stops++;
    EA = 1; /* replaces the adjacent SETB EA / ORL PCON instructions */
    BUTTON = 0;
    AUXINTIF |= 0x10;
    int2_isr();
}
static void advance(unsigned duration) {
    unsigned us;
    for (us = 0; us < duration; us += 20) {
        unsigned count;
        if (sleep_ready) standby();
        if (!TR0 || !ET0 || !EA) exit(2);
        count = ((unsigned)TH0 << 8) | TL0;
        count += 20;
        if (count >= 65536) {
            count = (count - 65536) + TIMER_RELOAD;
            samples++;
            timer0_isr();
        }
        TH0 = count >> 8;
        TL0 = count & 255;
        AVR_ONLINE = auto_ack ? BOOST : 0;
    }
}
int main(void) {
    unsigned phase, cycle;
    for (phase = 0; phase < 2; phase++) {
        pc_init(&controller);
        BUTTON = phase == 0; /* asleep then pressed, or already pressed */
        AVR_ONLINE = 0;
        sleep_ready = 1;
        ET0 = 1;
        TF0 = 1;             /* stale timer request must not survive STOP entry */
        stops = samples = 0;
        auto_ack = 1;
        standby();
        if (stops != (phase == 0)) return 1;
        /* Replay main every 20 us. Timer0 advances one count/us at 12T,
         * with EC78 auto reload. R1 resets it before any overflow occurs.
         */
        advance(100000);
        if (samples != 20 || controller.state != PC_ONLINE || !BOOST) return 3;
        if (AVR_BUTTON != 0 || AUXINTIF & 0x10) return 4;
        /* Exercise the actual driver's sleep request after full shutdown,
         * not just startup. All times align with 5 ms timer boundaries.
         */
        for (cycle = 0; cycle < 200; cycle++) {
            BUTTON = 1;
            advance(60000);
            if (!AVR_BUTTON || !BOOST) return 6;
            BUTTON = 0;
            advance(60000);
            if (AVR_BUTTON || !BOOST) return 7;
            BUTTON = 1;
            advance(60000);
            if (!AVR_BUTTON) return 8;
            auto_ack = AVR_ONLINE = 0;
            advance(505000); /* 10 ms filter plus 495 ms goodbye elapsed */
            if (!BOOST || controller.state != PC_SHUTDOWN) return 9;
            advance(5000);
            if (BOOST || controller.state != PC_WAIT_RELEASE) return 10;
            advance(5000);
            if (controller.state != PC_OFF || !sleep_ready) return 11;
            auto_ack = 1;
            advance(100000); /* simulated INT2 press wakes it again */
            if (!BOOST || controller.state != PC_ONLINE) return 12;
            if (stops != (phase == 0) + cycle + 1) return 13;
        }
        /* A stale main-loop decision must not stop an active timer. */
        sleep_ready = 0;
        TH0 = 0xf0;
        TL0 = 0x12;
        standby();
        if (!EA || !ET0 || !TR0 || TH0 != 0xf0 || TL0 != 0x12) return 14;
    }
    return 0;
}
'''
with tempfile.TemporaryDirectory(prefix='t7-standby-') as temp:
    src, exe = Path(temp) / 'standby.c', Path(temp) / 'standby'
    for fixed in [True, False]:
        target = driver
        if not fixed:
            start = target.index('static void standby(void)')
            end = target.index('void unused_target_main(void)')
            old = target[start:end].replace('sleep_ready = 0;', '')
            target = target[:start] + old + target[end:]
        src.write_text(target + test)
        subprocess.run(['cc', '-std=c99', '-Wall', '-Wextra', '-Werror', '-I.',
                        str(src), 'controller.c', '-o', str(exe)], check=True)
        result = subprocess.run([str(exe)])
        assert result.returncode == (0 if fixed else 3), (fixed, result.returncode)
print('Standby regression: R1 failure reproduced; R3 passed both wake paths and 400 shutdown/restart cycles.')
