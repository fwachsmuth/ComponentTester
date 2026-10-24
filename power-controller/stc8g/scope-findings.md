# R1 scope findings and R3 standby correction

User measurements and repository captures, received 2026-10-21. R1 remains
the installed firmware for these observations; R2 had only been prepared.

| Capture | Signals | Observation |
| --- | --- | --- |
| [32](../../DS1Z_QuickPrint32.png) | CH1 U5 pin 1, CH2 pin 7 | At 50 ms/div, output follows both button edges by about 40 ms. Debounce/timer operation while on is consistent with the design. |
| [33](../../DS1Z_QuickPrint33.png) | CH1 pin 1, CH2 pin 3 | Button input falls, converter enable stays low. User also checked for shorter pulses at faster scales and found none. |
| [34](../../DS1Z_QuickPrint34.png) | CH1 pin 3, CH2 pin 8 | Converter rises and AVR acknowledgment follows. Startup when the button is held during battery insertion works. |
| [35](../../DS1Z_QuickPrint35.png) | CH1 pin 3, CH2 pin 8 | Acknowledgment is already low throughout the pretrigger portion when converter enable falls. Its falling edge is not captured. |

U5 supply measured directly between pins 2 and 4: **3.8 V off, 4.7 V on**.
Pin 1 goes low when pressed in both states. Pin 7 follows while on and stays
low while off (as intended to avoid backfeeding the AVR). Ordinary restart
after shutdown also fails.

Capture 35 does **not** establish that the 500 ms shutdown delay is absent.
It is at 50 ms/div and has about six divisions (300 ms) of history before the
CH1 falling edge. The expected acknowledgment edge 500 ms earlier would lie
outside the left side of the displayed window. To measure it, trigger on the
falling edge of CH2/pin 8 at 200 ms/div, with sufficient posttrigger history.
The small CH2 rise after converter shutdown is not the requested shutdown edge.

## Concrete driver defect

R1 leaves `sleep_ready` set when returning from `standby()`. The main loop
therefore immediately calls `standby()` again. While the key is held low,
STOP is skipped but Timer0 is stopped and reloaded repeatedly before its
first 5 ms overflow. Consequently no new button samples arrive, the state
machine stays OFF, and converter enable stays low. Releasing the key lets
the driver re-enter STOP. Starting with the key already held avoids the
initial sleep request, explaining the successful forced startup.

R3 consumes the sleep request (`sleep_ready = 0`) before restarting Timer0,
on both return paths. The next timer sample can then run, debounce the key,
and enter BOOT. R3 retains the original low-power STOP/wake mechanism.

`test_standby.py` compiles the actual driver C with mocked SFRs and simulates
Timer0 advancement and the real main-loop decision. Removing the fix reproduces
zero timer samples and failure to boot. With the fix, 20 samples occur in
100 ms and startup reaches ONLINE, both after simulated INT2 wake and with
the button already low at standby entry. This verifies the control-flow
correction, not the physical chip's acceptance of the INT2 wake interrupt.

The review identified that CLKDIV is at extended address 0xFE01, not the
STC15 SFR address 0x97. The final review also established that stcgal may use
an oscillator/divider pair for its target clock, so R3 preserves the startup
configuration instead of overwriting either clock register. R1's measured
40 ms debounce supports its startup clock already being suitable.

## Prepared images

- **R3 STOP:** `build/t7-stc8g-power-r3-stop.hex`, 1,583 bytes. Contains the
  standby-request correction, stale-timer interrupt masking and preserved clock setup.
- **R2 IDLE fallback:** `build/t7-stc8g-power-r2-idle.hex`, 1,426 bytes. Keeps
  Timer0 running in standby, with higher and unmeasured standby consumption.

Both build and pass the state-machine, driver regression, generated-code and
HEX checks. Neither revised image has yet been tested on this T7. Both require
12 MHz oscillator trimming. No reflash was executed by the assistant.
