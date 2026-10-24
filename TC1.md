# TC1 graphical firmware

This checkout now defaults to the **ATmega324PA-U-TH TC1**, with a 16 MHz
crystal and a 128x160 ST7735 panel used in landscape (160x128).
It assumes U4 already runs the compatible tc1-u4 firmware.

The hardware settings are ported from
[Kernel-Error/tc1-firmware-update](https://github.com/Kernel-Error/tc1-firmware-update/tree/main/config).
Those files contain abbreviated/example patch sections, so the settings were
ported manually rather than applied with `patch`.
Both that project and this checkout's starting commit (`5d33dc9`) use **1.56m**;
this is a hardware/UI adaptation, not a newer measurement engine.

## Enhanced TC1 build (2026-10-23)

This separate profile brings the current T7 feature set to the original TC1,
including the working fast ST7735 transport and screen clearing, lossless
compact fonts/symbols, Exit first in the menu, 60-second auto-off in auto-hold,
capacitor voltage loss, BJT test current, and EIA-96 resistor markings.
It includes the tools described below and onboard IR/Zener support.

Build with:

```sh
python3 tools/build-tc1.py -j4
```

Output: `build/tc1-fast/ComponentTester-TC1-fast-display.hex`.
The build runs in a temporary directory and exports no default EEPROM image.
The old `sh tools/build-tc1.sh` command still builds the earlier profile
without the new hardware options; the historical sections below describe it.

The enhanced profile is `BOARD=TC1 DISPLAY_FAST=1`. Its battery correction is
**BAT_OFFSET=20 mV**: reduced from the inherited 290 mV after the user reported
a 270 mV high reading on the TC1. The T7 retains its separate 45 mV correction.
This is an offset adjustment based on that observation, not a multi-point
calibration. It uses these hardware assumptions:

- Onboard IR OUT: PD3, ATmega324PA physical pin 12, as on the T7.
- Zener measurement: PA4, physical pin 33, using the dedicated A/K contacts,
  A grounded and a continuously running boost converter. TC1 software uses
  R1=100000 and effective R2=11750 (factor 9.5106). This is a calibration
  parameter, not a claim that an 11.75k resistor was measured. The T7 keeps
  its separate 100k/12k calibration.
  Open the Zener menu tool to measure; double-press to exit.
- External reference: PA3, physical pin 34. Enabled with the original nominal
  **2495 mV**, not the measured T7-specific 2499 mV. The firmware accepts a
  reference reading only within 2.25-2.75 V; otherwise it falls back to its
  configured Vcc. A DMM check around 2.5 V confirms the expected hardware.

Do not flash the separate T7 STC8G power-controller firmware into TC1 U4.
Keep the compatible power firmware already working in this TC1.

Verified with AVR GCC 7.3.0: **32,744 / 32,768 bytes flash**, **252 bytes static
RAM**, and 22 bytes EEPROM defaults (not exported). Effective profile checks,
all 119 font glyphs/256 character mappings, 15 symbols at both sizes, passive
icons, display word transfer, and full/partial line clearing pass. The user confirmed the initial enhanced TC1 image works, but reported its
battery reading 270 mV high; the current build includes the correction above.
The corrected image still needs a hardware check. Both previous T7 rebuilds
were byte-identical to their working images.

Save any current adjustment to EEPROM in the tester menu, then back up the
**TC1's own** EEPROM before flashing:

```sh
avrdude -c avrispmkII -P usb -p m324pa -B 1 \
  -U eeprom:r:tc1-calibration-before-enhanced.eep:i
```

Only after the backup succeeds, flash and restore it:

```sh
avrdude -c avrispmkII -P usb -p m324pa -B 1 \
  -U flash:w:build/tc1-fast/ComponentTester-TC1-fast-display.hex:i \
  -U eeprom:w:tc1-calibration-before-enhanced.eep:i
```

SHA-256 of the enhanced HEX:
`0630628323d98e4316bdab8732138392c2f347673fe865b874a7ac69e9e5bba0`.

### TC1 Zener measurements (2026-10-24)

The reservoir capacitor pads were empty. Adding a 22 uF / 63 V low-ESR
capacitor removed the large ripple; no-load K then measured 46.2 V in the
Zener menu. The project's `Clones` hardware notes recommend a 100 V or higher
rated 10/22 uF replacement for this location.

Loaded measurements before the scale adjustment:

| Zener | K to GND (DMM) | PA4 to GND (DMM) | Display |
| --- | --- | --- | --- |
| 4.3 V | 4.07 V | 0.427 V | 3.975 V |
| 24 V | 24.17 V | 2.546 V | 23.46 V |

These imply divider factors 9.532 and 9.493, hence a software factor near
9.51. The new factor increases displayed voltage by about 1.9%, predicting
approximately 4.05 V and 23.91 V for unchanged ADC readings. At the higher
loaded point, the displayed value did not exactly match the independently
measured PA4 voltage times the old factor, so some measurement variability
remains. Connecting the DMM to PA4 did not change the displayed reading.

The no-load measurements (46.2 V at K, 4.63 V at PA4, display 43.2 V) imply a
different divider factor, about 9.98. This remains unexplained. The loaded
calibration deliberately does not try to force that open-circuit reading to
match: doing so would overcorrect the loaded Zener measurements. The physical
K-to-PA4 path is through a resistor marked 01D; no 200k resistor was measured.
Reference PA3 measured 2.491 V; AVCC measured 4.95 V.

## Screen changes

- 8x16 font: 20 columns and 8 rows, instead of the patch's 10x16 font
  (16 columns and 8 rows).
- White text on black, cyan headings, yellow measurement values and cursor.
- Yellow/green/red probe numbers, with reversed number glyphs.
- 30x32 semiconductor circuit symbols with probe numbers and pin labels.
- Additional 32x32 resistor and capacitor symbols at the top right.
  Resistor networks retain the full width for their connection diagram.
- Capacitance and ESR on separate rows; ESR is explicitly labeled.
- Battery icon and voltage in the bottom row after measurement.
- Centered startup/status messages and a question-mark symbol for failed tests.
- Auto-hold results; shorting all three probes opens the menu.
- Press the test button twice at startup to open the menu directly.
- Metric prefixes for readings such as `1.234k` instead of `1234`.

## Additional tools enabled

- **E24 resistor color bands** for matching 5% nominal values.
- **Potentiometer/trimmer information**: total resistance and divider ratios.
- **R/C/L monitor**: repeated measurements on probes 1 and 3.
- **Diode/LED quick-check**: repeated polarity and forward-voltage checks on
  probes 1 and 3; LEDs blink during the test.
- **ESR tool**: dedicated capacitor/ESR measurements, including in-circuit
  checks. Use discharged capacitors; parallel components can affect readings.
- **Reverse hFE**: transistor gain with collector and emitter reversed.
- **Capacitor leakage tool**: charging/leakage test on probes 1 (+) and 3 (-).
  This uses the tester's low supply voltage, not the capacitor's rated voltage.

The monitor, ESR and leakage tools use the existing single-button controls.
Two quick presses exit these tools. In the leakage tool a single press starts
charging; another stops charging and discharges the capacitor.

This uses the m-firmware UI and its existing paging behavior. It is not a
reproduction of the original factory screens. Measurement and detection
algorithms are unchanged. `UI_TC1` in `config.h` controls the additional passive
symbols and capacitor layout; the renderer requires this screen size and font.

## Hardware settings

| Function | TC1 connection |
| --- | --- |
| Probe ADC inputs 1/2/3 | PA0 / PA1 / PA2 |
| Probe 1 low/high resistors | PC0 / PC1 |
| Probe 2 low/high resistors | PC2 / PC3 |
| Probe 3 low/high resistors | PC4 / PC5 |
| Power hold / test button | PD2 / PD1 (button active low) |
| LCD reset / data-command | PB4 / PB5 |
| LCD data / clock | PB6 / PB7 (software SPI) |
| LCD orientation | Rotate, flip X, native X/Y offsets 2/1 |
| Battery ADC | PA5, direct measurement |
| Reference / Zener ADC | PA3 / PA4 (features disabled) |

The standard ST7735 driver is intentional, despite the source patch's
"semi-compatible" heading: its actual selection is `LCD_ST7735`.
Battery thresholds (3.4 V warning, 3.1 V shutdown) and the inherited 290 mV
offset follow the linked configuration. Compare displayed battery voltage
against a meter before adjusting `BAT_OFFSET`; it is not newly calibrated here.

PWM/squarewave generation is disabled: the firmware's timer output OC1B is PD4,
but the TC1's probe-2 resistor is PC2. Enabling the menu option cannot reroute
the timer signal. Hardware-dependent extras such as Zener boost control remain
disabled; this port does not establish their wiring.

## Build

Run from this checkout:

```sh
sh tools/build-tc1.sh -j4
```

The script uses `avr-gcc` on PATH, or the toolchain bundled with the legacy
`/Applications/Arduino.app` on macOS. For another installation, set
`ARDUINO_AVR_BIN` to its `bin` directory. Python 3 and a host C compiler are
needed for the checks. With an AVR toolchain already on PATH, `make -B -j4`
also builds the firmware directly.

Outputs are `ComponentTester.hex` (flash) and `ComponentTester.eep` (default
calibration data). Text and tables use flash (`DATA_FLASH`).

Verified here with AVR GCC 7.3.0 / avr-libc 2.0.0:

- Flash: **32,734 / 32,768 bytes**, only **34 bytes free**.
- Static RAM: **246 / 2,048 bytes**; this does not measure peak stack use.
- EEPROM defaults: **22 / 1,024 bytes**.
- Clean forced rebuild, effective configuration checks, and host tests of the
  production icon renderer passed without compiler warnings.

All additions fit by enabling link-time optimization and omitting the unused
Zener/crystal/OneWire bitmap tail. The bitmap tail is automatically restored
if those graphical features are enabled; existing symbol IDs remain unchanged.
The font, screen size and active component symbols are unchanged.
The build script verifies the final HEX address range against the actual 32 KiB
flash limit, because this older toolchain can link an oversized image without
failing. Another compiler version may produce a different size.

The renderer tests check the complete 1,024-pixel stream, panel offsets,
occupied-line tracking, cursor restoration, and invalid icon IDs.
The original graphical build was reported working on your TC1. This expanded
build and its new tools still require testing on the device.

## Flash and first test

U4 needs no further update for this build. Use the ISP setup that already
worked with your tester. To flash only the main firmware via Arduino as ISP,
substitute your actual serial device for `/dev/cu.YOUR_ISP_PORT`:

```sh
avrdude -c stk500v1 -b 19200 -P /dev/cu.YOUR_ISP_PORT -p m324pa \
  -U flash:w:ComponentTester.hex:i
```

This command changes neither fuses nor EEPROM. In particular, do not use
`make upload` merely to update flash: that target also writes the default
EEPROM image and resets existing calibration. The Makefile's programmer
default is still AVRISP mkII; override it to match your equipment if using
the Makefile programming targets. Keep the already-working TC1 fuses.

After flashing:

1. Check that the display is upright, complete, and shows the expected colors.
2. Check the button, power hold, and displayed battery voltage.
3. Short all three probes to enter the menu and run self-adjustment, following
   the firmware's short/remove-short/capacitor prompts.
4. Try a known resistor, capacitor, diode, and NPN/PNP transistor. Check both
   readings and pin labels, including the ESR row and battery footer.
5. Check the startup double-press shortcut and the new menu tools. For the
   leakage tool, begin with a discharged, correctly polarized capacitor.

If this is the previously working 1.56m `DATA_FLASH` setup, retaining EEPROM
avoids an unnecessary reset. To deliberately start with default calibration,
write the generated `.eep` separately and then run self-adjustment again.
No programming command has been executed as part of preparing this build.
