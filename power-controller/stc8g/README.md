# Experimental T7 STC8G power controller

This is a new, SDCC-buildable implementation of the replacement interface in
[atar-axis/tc1-u4](https://github.com/atar-axis/tc1-u4/blob/master/tc1-u4/main.c),
adapted for the **SOP8 STC8G1K08(A)** pin arrangement. It is not a direct rebuild
of the STC15 HEX and does not reproduce the unknown T7 factory protocol.
See the adjacent GPL-3.0 license and the SPDX notices in the source.

**Current revision: R3, corrected low-power STOP standby. Builds and passes
state-machine, driver regression and generated-image checks; R3 has not yet
been tested on physical hardware. R2 IDLE remains a fallback build.**

The R1 hardware test could start the tester when the button was held while
connecting the battery, and AVR-requested power-off worked. Normal startup
from standby failed. Scope captures confirmed correct button forwarding while
on, a valid button edge while off, and no converter-enable pulse on failed start.
Review found a concrete defect: R1 left `sleep_ready` set after wake-up, so
main repeatedly restarted Timer0 before a 5 ms sample could run. R3 clears
the request before restarting the timer and retains STOP standby. R2 removes
STOP entirely but has higher and unmeasured standby consumption. See
[scope findings](scope-findings.md) for evidence and test limitations.

Holding the key during initial AVR startup selects continuous measurement mode
in the AVR firmware, so R1's repeated measurements in that test were expected.
U5 was identified by its bootloader as **STC8G1K08-8PIN, F7A4**, not the A
variant. BSL is 7.3.12U, with an existing clock of 23.938 MHz. See
[factory-identification.txt](factory-identification.txt) for the original options.
Do not substitute this file for the working TC1 STC15 firmware.

## Board mapping

| U5 pin | Signal | Evidence on this T7 |
| --- | --- | --- |
| 1 | P5.4, active-low button | Reported 4.5 V released, 0 V pressed |
| 2 | VCC | Reported 4.0 V off, 4.1 V on in latest measurements |
| 3 | P5.5, active-high converter enable | Reported 0 V off, 4.1 V on; role inferred from behavior and reference design, not traced to converter |
| 4 | GND | Manufacturer pinout; board continuity to battery negative still to verify |
| 5 | P3.0, bootloader RX | Manufacturer pinout; PCB routing unverified |
| 6 | P3.1, bootloader TX | Manufacturer pinout; PCB routing unverified |
| 7 | P3.2, AVR button output | 0 ohms to ATmega PD1, TQFP pin 10 |
| 8 | P3.3, AVR online input | 0 ohms to ATmega PD2, TQFP pin 11 |

Manufacturer sources:

- [STC8G1K08 pinout, page 12](https://www.stcmicro.com/datasheet/STC8G1K08_Features.pdf#page=12)
- [STC8G1K08A features and SOP8 pinout](https://www.stcmicro.com/datasheet/STC8G1K08A_Features.pdf)
- [STC8G reference manual](https://www.stcmicro.com/datasheet/STC8G-en.pdf),
  clock division, GPIO modes, interrupt flags, Timer 0 and power-down chapters.

## Implementation

- P5.4 replaces STC15 P3.4 for the physical button.
- P5.5 replaces STC15 P3.5 for converter enable.
- P3.2/P3.3 retain the AVR button/acknowledgment interface.
- Timer 0 mode 0 supplies a 5 ms tick at **12 MHz effective CPU clock**, with
  the timer in 12T mode. No Timer 2 is required.
- Preserve the oscillator/divider configuration installed by `stcgal -t 12000`.
  The programmer may use a divider to obtain the target frequency. Neither
  the STC8G extended CLKDIV nor the old STC15 SFR address is written.
- The button changes state after eight matching samples (40 ms). Intermediate
  bouncing retains the previous state.
- AVR acknowledgment has a two-sample filter (10 ms). Startup allows 1 s for
  the acknowledgment; normal AVR shutdown allows 500 ms for the goodbye screen.
- Holding the key after shutdown or failed startup does not repeatedly reboot
  the AVR; release is required before the next startup.
- A held key is forwarded to the AVR. There is no independent long-press power
  off: the AVR requests shutdown by dropping PD2.
- R3 standby drives both outputs low and stops Timer0 while in STOP; INT2
  wakes on P5.4. Returning from standby consumes the sleep request before
  restarting Timer0, allowing the next sample to debounce the key.
- Timer0's interrupt is masked and its pending flag cleared before STOP;
  its interrupt is restored after restarting the timer.
- R2 fallback keeps Timer0 running and uses IDLE even while the converter
  is off. It does not depend on INT2 wake-up.
- GPIO inputs use quasi-bidirectional mode/weak pull-ups as in the reference;
  outputs use push-pull mode. UART pins are left untouched.

R3's physical wake-up/start/restart and standby current need hardware
verification. Host tests cannot validate those peripherals.
In particular, a floating AVR acknowledgment input can be pulled high: the boot
timeout test assumes the connected AVR actually holds its acknowledgment low.

## Build and tests without Keil

```sh
make -C power-controller/stc8g
```

Requires SDCC, `packihx`, and a host C compiler. SDCC 4.6.0 was installed via
`brew install sdcc` for this build. Output:

`build/t7-stc8g-power-r3-stop.hex` (preferred next test)

`build/t7-stc8g-power-r2-idle.hex` (fallback without STOP standby)

The final reviewed R3 build occupies **1,583 / 8,192 bytes** of code address
space; R2 uses **1,426 bytes**.
The compiler reports stack starting at 0x22 with 222 bytes available; this is
not a measurement of peak stack use. No external RAM is allocated.

Tests exercise the production `controller.c` logic: idle, bouncing contacts,
debounce boundaries, startup timeout, acknowledgment, normal/held button
forwarding, acknowledgment glitches, delayed shutdown and release-before-restart.
An additional test covers starting after prolonged powered standby. A driver
regression reproduces R1 timer starvation and verifies R3 on both standby
return paths, including 400 full simulated shutdown/restart cycles. Generated
assembly and linked-image checks verify register addresses, interrupt vector
destinations, standby-request ordering, interrupt masking, preserved clock
configuration, valid HEX checksums and code within the 8 KiB limit. R2 is also
checked to contain no STOP routine.

## Identify U5 before programming

With U5 isolated from the board's other power sources, use the same true 3.3 V
USB/UART arrangement as for the previous TC1 controller, adjusted to this pinout:

| USB/UART | U5 |
| --- | --- |
| TX, 3.3 V logic | pin 5, RX |
| RX | pin 6, TX |
| GND | pin 4 |
| Switched 3.3 V supply | pin 2 |

Do not combine the external supply with the T7 battery or USB charging power.
In-circuit programming has not been established for this board. First verify
the pin-1 orientation and pin-4 ground connection. Identification does not
require altering flash or setting the oscillator frequency:

```sh
stcgal -P stc8g -p /dev/cu.YOUR_UART_PORT -l 2400
```

Start the command before powering U5. Explicit `stc8g` mode was necessary on
this setup: it uses even parity and checksum validation. `auto` yielded rejected
frames and one unreliable EEA4 identifier, followed by an unknown-model crash.
Avoid parasitic powering through UART leads during the power-off interval.
This chip remained at about 3.05 V with VCC disconnected but UART attached;
with only GND attached it fell to 0.04 V. Disconnect/reconnect VCC, TX and RX
together for a clean power cycle, keeping the USB adapter itself connected.
With **no image argument and no `-e`**, the installed stcgal 1.10 connects,
reports the device, and disconnects; its local frontend source was checked.
This identifies the MCU but does not back up its factory application.

The successful identification confirms 8 KiB code flash, GPIO operation of
pin 1 (`reset_pin_enabled=False`), and watchdog disabled at power-on. The
experimental build requires a **12 MHz internal clock**, so the existing
23.938 MHz setting must be changed when programming.

## Program the experimental controller

From the ComponentTester repository root, with the isolated chip connected:

```sh
stcgal -P stc8g -p /dev/cu.usbserial-A50285BI -l 2400 -b 19200 \
  -t 12000 -o eeprom_erase_enabled=false \
  power-controller/stc8g/build/t7-stc8g-power-r3-stop.hex
```

This replaces U5's current application with **R3**, which still needs hardware
testing. It requests 12 MHz oscillator trimming and disables the EEPROM
erase option; other reported configuration settings are retained. The recorded
identity is not a backup of the original program. R1 was already flashed by the
user and clock trimming to 11.998 MHz succeeded. No flashing command has been
executed by the assistant, and the Makefile has no automatic programming target.

Use the same clean power-cycle procedure that produced the valid identification.
Check the adjusted frequency and successful programming output. **Before
reinstalling, follow the [loose-chip bench test](bench-test.md)** to check
normal wake-up, forwarding, shutdown and restart without another soldering
cycle. Afterward, reinstall in the recorded orientation and check short/held presses,
AVR-requested shutdown, and standby current. The replacement does not implement
the factory controller's independent long-press power-off behavior: it forwards
the held button to the AVR, which is responsible for requesting shutdown.

The T7's incorrect battery display is a separate AVR diagnostic issue and is
not corrected by this controller build.
