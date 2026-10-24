# Test the programmed U5 before soldering it back

This tests wake-up, GPIO and timing on the actual loose chip. It cannot test
the T7 converter load or the real AVR, which are absent from this setup.

Use the same verified top-view SOP8 orientation as for programming. Keep the
chip continuously powered during the tests below. Use **3.3 V on pin 2**,
**GND on pin 4**, and preferably 100 nF directly across pins 2 and 4. After
flashing, disconnect the UART wires from pins 5 and 6. All scope grounds go
to pin 4. Leave pin 1 open except when simulating a press; firmware enables
its weak pull-up. Use a **1 kOhm series resistor** in each of the two input
jumper leads (pins 1 and 8).

1. **Set simulated AVR acknowledgment high.** Connect pin 8 through its 1 kOhm
   resistor to 3.3 V. This substitutes for a running AVR's PD2 output. With
   pin 1 released, wait at least two seconds. Pin 3 should be low: the
   controller must not turn the converter on merely because acknowledgment
   is high.
2. **Start from standby.** Connect pin 1 through its 1 kOhm resistor to GND
   for about 100 ms, then release it. Pin 3 should rise after about 40 ms
   plus oscillator wake-up time and stay high. Pin 7 should be low while
   the debounced button is held, then high after release.
3. **Check forwarding while on.** Press/release pin 1 again. Pin 7 should
   follow its edges with about 40 ms debounce delay; pin 3 should stay high.
4. **Request shutdown.** Move the pin-8 input jumper from 3.3 V to GND,
   keeping its series resistor. Pin 3 should fall after about 510 ms
   (10 ms input filtering plus 500 ms shutdown delay). Pin 7 should become
   low. Leave pin 1 released and wait at least two seconds.
5. **Restart.** Move pin 8 back to 3.3 V; pin 3 should remain low. Press and
   release pin 1 as in step 2. It should start again. Repeat steps 4 and 5
   several times, including a longer standby wait.
6. **Optional startup timeout.** Request shutdown, leave pin 8 low and wait
   two seconds. Press pin 1: pin 3 should rise, then fall about one second
   later without acknowledgment. Release pin 1 before the next attempt.

If normal wake-up or restart fails here, keep the chip in the programming
setup for diagnosis rather than soldering it back. R2 IDLE remains an
available fallback image. If these checks pass, reinstall in the recorded
orientation and repeat normal startup/shutdown on the complete T7.

## Review and build checks, 2026-10-21

The final reviewed R3 image is **1,583 bytes**. `stcgal` should report this
when loading it. SHA-256 of the Intel HEX file:

```text
bb836823fec4de2401ece856765bd5704533441c76f2b1d3db05f8296a1b5d2f
```

The review confirmed:

- Clearing `sleep_ready` before restarting Timer0 on both standby return paths.
- Masking Timer0 and clearing stale TF0 before STOP, then restoring Timer0's
  interrupt on return. INT2 is the wake source during STOP.
- Preserving the clock configuration installed by `stcgal -t 12000`: the
  programmer can select an oscillator/divider pair, so forcing CLKDIV to zero
  could invalidate calibration. No clock-selection/divider register is written.
- Correct pin bit-addresses and SFR addresses in the linker output, and actual
  reset/Timer0/INT2 LJMP destinations in the final HEX.
- Reproduction of R1 starvation without the fix and successful R3 control flow
  for both wake paths and **400 full simulated shutdown/restart cycles**.
- Existing debounce, held-button, acknowledgment filtering, boot timeout,
  delayed shutdown and release-before-retry tests pass.

The driver regression compiles the actual C driver with mocked registers and
simulated timer/INT2 behavior. It does not prove physical wake-up or measure
standby current. The loose-chip procedure above covers the main remaining
hardware uncertainty before reinstalling U5.
