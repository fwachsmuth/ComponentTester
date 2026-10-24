# ComponentTester firmware for TC1 and T7

Graphical firmware for two ATmega324PA component testers, based on Markus
Reschke's **m-firmware 1.56m** and forked from
[Ho-Ro/ComponentTester](https://github.com/Ho-Ro/ComponentTester).
This fork adapts the hardware configuration, display and controls, adds build
tools and tests, and supplies a separate replacement T7 power-controller firmware.
The underlying component measurement engine remains m-firmware 1.56m.

The original English manual is preserved unchanged as
[README.upstream](README.upstream); the original German manual is
[README.de](README.de). Detailed development and measurement notes are in
[TC1.md](TC1.md), [T7.md](T7.md), and
[power-controller/stc8g/README.md](power-controller/stc8g/README.md).
Those notes include historical configurations; the commands and target table
below describe the current builds.

- [Features](#what-this-fork-adds) · [TC1/T7 differences](#targets-and-firmware-files)
- [Release downloads](#download-ready-built-firmware) · [Mac builds](#build-on-macos)
- [AVRISP mkII flashing](#flash-the-atmega-using-avrisp-mkii)
- [USB–serial flashing](#flash-an-stc-power-controller-using-usbserial)
- [Zener calibration](#calibrate-the-dedicated-zener-input)

## What this fork adds

There are two kinds of firmware changes here: existing m-firmware capabilities
selected/configured for these boards, and code implemented by this fork. The
comparison below is against the original **1.56m** checkout (`5d33dc9`).

### Existing upstream features enabled or configured here

These capabilities already exist in m-firmware; this fork enables them and sets
the wiring, geometry, colors or calibration values needed by the documented TC1
and T7. They are not new measurement algorithms written for this fork.

| Upstream capability | Configuration in this fork |
| --- | --- |
| ST7735 color display, fonts, semiconductor symbols, colored probe numbers and battery indicator | Landscape orientation, offsets, existing 8×16 font, white/cyan/yellow palette and battery footer; configured in `config.h`, `config_644.h` and `colors.h` |
| Hardware support and voltage corrections | ATmega324PA at 16 MHz; probe, LCD and button wiring; battery offsets; 2.5 V reference; onboard IR on PD3; dedicated A/K Zener input and divider scaling |
| Auto-hold and menu shortcuts | `UI_AUTOHOLD`, `UI_SHORT_CIRCUIT_MENU`, `UI_MAINMENU_POWERON_BUTTON` |
| Automatic shutdown | Existing `POWER_OFF_TIMEOUT=60` in auto-hold and five-empty-test cutoff; the fork also makes a small implementation optimization described below |
| Resistor information | E24 color bands, EIA-96 markings and trimmer total/ratio (`SW_R_E24_5_CC`, `SW_R_E96_EIA96`, `SW_R_TRIMMER`) |
| Additional measurement information | Capacitor voltage loss, BJT test current and reverse hFE (`SW_C_VLOSS`, `SW_HFE_CURRENT`, `SW_REVERSE_HFE`) |
| Measurement tools | ESR, capacitor leakage, R/C/L monitor, diode/LED quick-check, optocoupler testing, self-test, adjustment and calibration save/load |

The battery and Zener corrections are board-specific **settings derived from
measurements**, using upstream correction mechanisms. Likewise, reference
measurement and IR decoding use upstream code. The existing [tc1-u4 project](https://github.com/atar-axis/tc1-u4)
provides the TC1's separate STC15 controller firmware; that firmware was not
implemented by this fork.

### Firmware code implemented by this fork

- **T7 STC8G power controller:** a separate SDCC implementation for the
  STC8G1K08, following the button/power interface described by tc1-u4. It adds
  the STC8G GPIO/timer setup and R3 STOP/wake handling, including fixes for
  standby restart. Sources: [power-controller/stc8g](power-controller/stc8g).
  R3 was confirmed working on the documented T7; reported whole-board
  switched-off current was 0.25 mA.
- **Faster ST7735 transfers and compatible clearing:** a fixed-wiring AVR
  assembly writer sends each 16-bit pixel with fewer CPU cycles. Screen erasure
  uses the same working transfer timing. This is the fork's own transport in
  [ST7735_fast.h](ST7735_fast.h), integrated into [ST7735.c](ST7735.c), with no
  OneBitDisplay dependency.
- **Lossless font and symbol compression:** new packed tables and decoding paths
  retain the existing upstream glyphs and semiconductor symbols while reducing
  flash use. Unused optional symbol tails are omitted conditionally, with symbol
  IDs preserved. This helps fit the selected features into 32 KiB; the existing
  font and semiconductor artwork are not claimed as new designs.
- **Additional passive-component icons and layout:** new resistor/capacitor
  artwork and a renderer place 32×32 icons at the top right. Capacitor ESR moves
  to a separate labeled row. The `UI_TC1` code in [ST7735.c](ST7735.c) and
  [main.c](main.c) implements this for both targets; an accompanying string guard
  keeps the ESR label available independently of the dedicated ESR tool.
- **Exit first in the menu:** [user.c](user.c) changes the item order for the TC1
  and T7 profiles so Exit is the initially selected entry. Upstream's menu and
  single-button navigation are retained.
- **Smaller auto-off bookkeeping:** [user.c](user.c) uses an 8-bit timeout
  counter for settings up to 127 seconds, retains a 16-bit counter for longer
  settings, and simplifies the timeout tick handling. Automatic shutdown itself
  is an upstream feature.

### Build, test and documentation additions

- Separate `BOARD=TC1` / `BOARD=T7` profiles and isolated build wrappers in
  [tools](tools), with explicit compiler/linker size optimizations so both builds
  retain the selected tools. These are build changes, not new test modes.
- Font/symbol packing generators and [tests](tests) for effective configuration,
  HEX limits/checksums, original-versus-packed pixels, display transfers and line
  clearing. The STC8G directory also adds controller, standby and linked-image
  checks.
- Ready-built [release assets](https://github.com/fwachsmuth/ComponentTester/releases/latest)
  with checksums, Mac build/flashing instructions, board measurement notes and
  the Zener calibration procedure below.

Short all three numbered probes to enter the menu, or press the button twice
at startup. Short presses advance menu items; hold to select. The Zener tool
uses the dedicated **A/K contacts** and exits with two quick presses. Capacitor
leakage testing uses the low tester supply voltage, not the capacitor's rating.
PWM/square-wave output is disabled because the timer output is not routed to
the required probe on these boards.

## Targets and firmware files

Both documented testers have an **ATmega324PA, 16 MHz crystal**, and a 128×160
ST7735 display used as 160×128. Product names alone do not identify a PCB revision;
verify your MCU, power controller and wiring before choosing an image.

| Setting | TC1 | Blue-PCB T7 |
| --- | --- | --- |
| Main AVR image | `ComponentTester-TC1-fast-display.hex` | `ComponentTester-T7-fast-display.hex` |
| AVR programming | AVRISP mkII, SPI ISP | AVRISP mkII, SPI ISP |
| Header on the documented board | 6-pin | 10-pin; map signals rather than assuming orientation |
| Power controller | U4, STC15L104W; compatible [tc1-u4](https://github.com/atar-axis/tc1-u4) firmware | U5, identified as STC8G1K08-8PIN, model F7A4 |
| Power-controller image | External tc1-u4 image; not built here | `t7-stc8g-power-r3-stop.hex`, built here |
| `BAT_OFFSET` | 20 mV | 45 mV |
| `UREF_25` | 2495 mV nominal; measured about 2491 mV | 2499 mV, measured |
| Zener software `R1` / `R2` | 100000 / 11750 Ω, effective calibration | 100000 / 12000 Ω |
| Zener multiplier | About 9.51 | About 9.333 |
| Onboard IR input | PD3, physical pin 12, using the shared mapping | PD3, physical pin 12, traced and verified |
| Zener / reference / battery ADC | PA4 pin 33 / PA3 pin 34 / PA5 pin 32 | Same |

The TC1's latest Zener correction was calculated from loaded DMM measurements;
that exact correction still needs confirmation after flashing. Its unloaded
voltage discrepancy remains unexplained. The TC1 also needed its missing boost
reservoir capacitor restored. See the calibration guide below.

The T7 also has `ComponentTester-T7.hex`, with the same features and the original,
slower display transport. Do not interchange the TC1 and T7 power-controller
images or their EEPROM calibration backups.

## Download ready-built firmware

Get the HEX files and `SHA256SUMS.txt` from
[GitHub Releases](https://github.com/fwachsmuth/ComponentTester/releases/latest).
The release includes the two fast-display AVR images, the standard-display T7
image, and the separate T7 STC8G R3 image. Historical experiments are excluded.

With all downloaded assets in the same directory, verify them on macOS:

```sh
shasum -a 256 -c SHA256SUMS.txt
```

The following build commands produce the same filenames under `build/`.
When flashing a downloaded asset, substitute its actual path in the commands.

## Build on macOS

### Install the tools

Install [Homebrew](https://brew.sh/) first if needed. Then:

```sh
xcode-select --install
brew install python pipx avrdude sdcc arduino-cli
```

If Xcode command-line tools are already installed, skip the first command.
`sdcc` and its `packihx` utility are only needed for the T7 power controller;
`pipx`/`stcgal` are only needed for serial programming of an STC controller.

Check which Python your shell selects before installing Python tools:

```sh
command -v python3
python3 -c 'import sys; print(sys.executable)'
python3 -m pip --version
```

If it selects Apple's/Xcode's Python instead of Homebrew, initialize the matching
Homebrew installation in this shell. On Apple Silicon:

```sh
eval "$(/opt/homebrew/bin/brew shellenv)"
rehash
```

On an Intel Mac, use `/usr/local/bin/brew` instead. Install the STC programmer
in its own environment:

```sh
pipx install --python "$(brew --prefix)/bin/python3" stcgal
pipx ensurepath
```

Open a new terminal if `stcgal` is not yet on `PATH`.

### Select the AVR compiler

The release builds were verified with **AVR GCC 7.3.0**. There are only **24 bytes
free** in each current fast-display AVR image, so a different compiler can
change the size enough to exceed flash. The build checks reject oversized HEX
files. The [Homebrew AVR tap](https://github.com/osx-cross/homebrew-avr) currently
does not provide GCC 7; do not assume its default compiler reproduces this build.

A way to obtain Arduino's GCC 7.3.0 toolchain is to install its pinned AVR core
using the [Arduino CLI](https://docs.arduino.cc/arduino-cli/installation/).
The [Arduino package index](https://downloads.arduino.cc/packages/package_index.json)
lists that compiler as a dependency of AVR core 1.8.6:

```sh
arduino-cli core update-index
arduino-cli core install arduino:avr@1.8.6
export ARDUINO_AVR_BIN="$HOME/Library/Arduino15/packages/arduino/tools/avr-gcc/7.3.0-atmel3.6.1-arduino7/bin"
export PATH="$ARDUINO_AVR_BIN:$PATH"
avr-gcc --version
```

This path assumes Arduino CLI's default macOS data directory. If you configured
a different one, adjust it. Arduino's packaged Mac compiler is an Intel binary;
Apple Silicon Macs need Rosetta to run it. The build scripts also support the
legacy Arduino installation at
`/Applications/Arduino.app/Contents/Java/hardware/tools/avr/bin` as a fallback.
Setting `ARDUINO_AVR_BIN` only selects that fallback when `avr-gcc` is absent
from `PATH`; putting the desired directory first in `PATH` selects it explicitly.

Arduino is used here to obtain the compiler. These are Makefile builds, not
Arduino sketches, and no Arduino bootloader is installed.

### Build the AVR images

```sh
git clone https://github.com/fwachsmuth/ComponentTester.git
cd ComponentTester
python3 tools/build-tc1.py -j4
python3 tools/build-t7.py --fast-display -j4
```

| Build | Output |
| --- | --- |
| TC1 fast display | `build/tc1-fast/ComponentTester-TC1-fast-display.hex` |
| T7 fast display | `build/t7-fast/ComponentTester-T7-fast-display.hex` |

For the T7's original display transport:

```sh
python3 tools/build-t7.py -j4
```

Output: `build/t7/ComponentTester-T7.hex`.

These scripts force a rebuild in a temporary directory, run the relevant checks,
and export HEX, ELF and map files. They do not flash a device or export default
EEPROM data. Use these commands rather than plain `make` or
`sh tools/build-tc1.sh`: those retain the older default TC1 configuration.

### Build the T7 power controller

```sh
make -C power-controller/stc8g
```

Output: `power-controller/stc8g/build/t7-stc8g-power-r3-stop.hex`.
This uses SDCC, not Keil. The build also runs host/standby tests and checks the
linked images. It additionally produces an R2 IDLE fallback; R3 STOP is the
version confirmed working on the documented board. TC1 U4 firmware is an external
Keil project; use a suitable prebuilt image from
[atar-axis/tc1-u4](https://github.com/atar-axis/tc1-u4) rather than this T7 binary.

## Flash the ATmega using AVRISP mkII

The ATmega measurement/display firmware is programmed over **SPI ISP**. A normal
USB–serial adapter cannot upload these AVR images to the documented testers.

Connect MOSI, MISO, SCK, RESET, GND and target-voltage sense to the corresponding
board nets. Verify header orientation and continuity, especially on the T7's
10-pin connector. The display's software-SPI data pin is not the AVR's hardware
MOSI signal; use the board's actual ISP signals.

The [AVRISP mkII does not power the target](https://onlinedocs.microchip.com/oxy/GUID-BEB648AA-8539-418A-9EFB-118BDC9DC77B-en-US-2/GUID-5A5D89A1-087A-4A10-8635-36F265BC4207.html).
Power the board separately and connect VTG to its AVR supply for voltage sensing.
Keep the board powered throughout the operation. These commands assume the
documented ATmega324PA/16 MHz setup and do not change fuses or lock bits.

Check connectivity without programming:

```sh
avrdude -c avrispmkII -P usb -p m324pa -B 1 -n -v
```

Choose the image and a backup filename for **this device**. For TC1:

```sh
AVR_IMAGE=build/tc1-fast/ComponentTester-TC1-fast-display.hex
EEPROM_BACKUP=tc1-calibration-before-flash.eep
```

For T7, use these assignments instead:

```sh
AVR_IMAGE=build/t7-fast/ComponentTester-T7-fast-display.hex
EEPROM_BACKUP=t7-calibration-before-flash.eep
```

First save any current adjustment through the tester's **Save** calibration menu.
Keep an existing backup safe; choose a new filename if necessary. Then back up
EEPROM and flash **only if that backup succeeds**:

```sh
avrdude -c avrispmkII -P usb -p m324pa -B 1 \
  -U "eeprom:r:$EEPROM_BACKUP:i" &&
avrdude -c avrispmkII -P usb -p m324pa -B 1 \
  -U "flash:w:$AVR_IMAGE:i" \
  -U "eeprom:w:$EEPROM_BACKUP:i"
```

The flash chip erase can erase EEPROM depending on EESAVE, so restore the backup
in the same programming invocation. Do not use the upstream `make upload` target:
it also writes default EEPROM. Factory read protection may prevent a usable
backup; do not erase/unlock a chip expecting that to recover its original data.

Disconnect the programmer after success. Check startup, button operation, a
known component, battery voltage and automatic shutdown. Calibration belongs to
the individual tester; never restore another board's EEPROM as its calibration.

## Flash an STC power controller using USB–serial

This is a separate chip and a separate firmware image. If the compatible power
controller already works, updating the AVR alone does not require reflashing it.
The tester's USB charging socket is not the programming connection described here.

Use a **3.3 V supply and 3.3 V UART logic**, with the controller isolated from
the board's battery/USB power. Loose-chip programming was used successfully;
in-circuit programming on the T7 has not been established. Confirm the chip
marking and pin-1 dot before wiring.

For the documented SOP8 TC1 STC15L104W and T7 STC8G1K08 controllers:

| USB–serial adapter | Controller pin |
| --- | --- |
| Switched 3.3 V supply | 2, VCC |
| GND | 4, GND |
| TX, through approximately 220 Ω | 5, MCU RX / P3.0 |
| RX | 6, MCU TX / P3.1 |

Place a 100 nF decoupling capacitor across pins 2 and 4 near the chip. TX/RX
names in this table are from the adapter's perspective; board header labels can
be reversed. Verify actual connections rather than relying on those labels.
TC1 wiring is also documented by
[Kernel-Error's flashing guide](https://github.com/Kernel-Error/tc1-firmware-update).

Find the adapter and set its actual port:

```sh
ls /dev/cu.*
STC_PORT=/dev/cu.usbserial-YOUR_ADAPTER
```

### T7 U5: STC8G1K08

Test connectivity first, with no image and no erase flag:

```sh
stcgal -P stc8g -p "$STC_PORT" -l 2400
```

Start the command with the chip unpowered, then apply power when prompted.
Expect **STC8G1K08-8PIN / F7A4** on the documented board. Explicit `-P stc8g`
selects the correct protocol, including parity; there is no extra parity flag
to add. `auto` produced unreliable identification on this setup.

If the chip stays powered through the UART leads, disconnect VCC, TX and RX
together, leaving GND connected, then reconnect them when prompted. Keep the
USB adapter itself attached to the Mac. Unplugging it removes the serial port
and causes `Device not configured` errors.

Program R3 from the repository root:

```sh
stcgal -P stc8g -p "$STC_PORT" -l 2400 -b 19200 \
  -t 12000 -o eeprom_erase_enabled=false \
  power-controller/stc8g/build/t7-stc8g-power-r3-stop.hex
```

`-l` is handshake baud, `-b` is transfer baud, and `-t 12000` requests the
**12 MHz** oscillator calibration required by this firmware. Identification alone
does not back up the factory program. Follow the
[loose-chip bench procedure](power-controller/stc8g/bench-test.md) before soldering
it back, then check normal wake-up, short/held presses, shutdown and restart.

### TC1 U4: STC15L104W

Use the compatible external [tc1-u4 firmware](https://github.com/atar-axis/tc1-u4),
whose project supplies a prebuilt `u4.hex`; it also requires a 12 MHz clock.
For an identified STC15L104W, the equivalent stcgal commands are:

```sh
stcgal -P stc15 -p "$STC_PORT" -l 2400
```

After downloading the correct external image, substitute its path here:

```sh
stcgal -P stc15 -p "$STC_PORT" -l 2400 -b 19200 \
  -t 12000 -o eeprom_erase_enabled=false /path/to/u4.hex
```

Use the same clean power-cycle procedure. This fork does not include/build that
STC15 image. Do not substitute the T7 STC8G HEX. See
[stcgal usage](https://github.com/grigorig/stcgal/blob/master/doc/USAGE.md) for
protocol and option details.

## Calibrate the dedicated Zener input

Use the **DMM voltage actually across the diode**, not its nominal marking:
a 4.3 V Zener need not measure exactly 4.3 V at the tester's available current.
The procedure below separates supply, wiring and scaling errors before changing
firmware. All voltages are relative to battery negative/GND.

### 1. Verify the hardware path and supply

With power removed and the high-voltage node discharged, trace:

```text
transformer → rectifier → reservoir capacitor → feed resistor → K
                                                              |
                                                        upper sense R1
                                                              |
                                                     PA4, AVR pin 33
                                                              |
                                                        lower sense R2
                                                              |
                                                             GND
A ─────────────────────────────────────────────────────────── GND
```

Confirm A-to-GND continuity and that the divider reaches the configured ADC
input. On these boards, `TP_ZENER=PA4` in `config_644.h`. Record resistor markings
and measurements. The approximately 10k feed resistor is separate from the
approximately 100k upper sense resistor. In-circuit resistance can include other
paths, and different probe-polarity readings do not establish an exact value.

Reconnect the battery, leave USB/ISP disconnected, and check K and the reservoir
node in normal mode and in the Zener menu. Use a scope if available: a severely
rippling boost supply must be fixed before calibrating its voltage scale. The
documented TC1 had empty reservoir-capacitor pads and initially only about
6–12 V at K. Adding a reservoir capacitor removed the ripple and produced
approximately 46 V unloaded. Upstream [TC1 hardware notes](Clones) recommend
10 or 22 µF low-ESR capacitance rated **100 V or higher**, across rectifier output
and GND, before the feed resistor. Confirm the pad connections and polarity.

Do not connect the high-voltage K node to the numbered component probes or an
ADC pin directly. Keep the divided ADC voltage within the MCU's supply range.
Measure residual voltage before using resistance mode or working on the circuit.

### 2. Record loaded voltage pairs

Connect a Zener with cathode/band to K and anode to A, open the Zener menu, and
record:

| Measurement | Purpose |
| --- | --- |
| K → GND with the DMM | Actual diode voltage |
| Pin 33 → GND with the DMM | Divider output presented to the AVR |
| Tester display | End-to-end firmware reading |
| Display with/without DMM on pin 33 | Check whether the meter loads the sense node |

Repeat with at least two substantially different diode voltages, preferably
three. Keep readings close together in time and allow the circuit to settle.
Also record AVCC (physical pin 27) and the external reference on PA3 (pin 34),
expected near 5 V and 2.5 V on these boards. Avoid bridging adjacent MCU pins;
an accessible resistor pad on the same net is easier to probe.

### 3. Calculate and adjust the Zener scale

The custom-divider firmware uses:

```text
displayed voltage = ADC voltage × (R1 + R2) / R2
measured divider factor F = DMM voltage at K / DMM voltage at pin 33
effective R2 = R1 / (F − 1)
```

If several loaded pairs give a consistent F and the displayed voltage agrees
with the ADC-node voltage times the configured factor, change the matching
board's `ZENER_R1` / `ZENER_R2` in **config.h**. Keep a confirmed upper resistor
as R1 and calculate an effective R2. This is a software calibration parameter;
it does not mean a resistor of that exact value was measured or must be fitted.

Our TC1 example, before correction:

| Diode | K, DMM | Pin 33, DMM | Display | K / pin 33 |
| --- | --- | --- | --- | --- |
| 4.3 V | 4.07 V | 0.427 V | 3.975 V | 9.532 |
| 24 V | 24.17 V | 2.546 V | 23.46 V | 9.493 |

A factor around **9.51** gives effective R2 ≈ **11750 Ω** with R1=100000 Ω.
That replaces the copied T7 factor of 9.333 (100000/12000 settings), increasing
the displayed value by about 1.9%. The 24 V example still shows some discrepancy
between the DMM ADC reading and the displayed value; the scale change alone
does not establish perfect agreement at every voltage.

Alternatively, with a stable supply and consistent display errors, a DMM/display
pair gives `new factor = old factor × DMM voltage / displayed voltage`. Check
several voltages before choosing a correction. If the factors disagree materially,
investigate supply ripple, loading, ADC/reference behaviour and the actual path
instead of fitting one reading. In particular, our TC1's unloaded measurements
implied about 9.98, unlike the loaded measurements: calibrating to that unloaded
point alone would overcorrect the actual diode readings.

Relevant settings and their scope:

| Parameter | What to adjust |
| --- | --- |
| `TP_ZENER`, `config_644.h` | ADC channel, only if continuity proves different wiring |
| `HW_ZENER`, `config.h` | Enables the dedicated Zener tool |
| `ZENER_UNSWITCHED`, `config.h` | Matches an always-running boost supply; different boost control needs its own verified configuration |
| `ZENER_DIVIDER_CUSTOM`, `ZENER_R1`, `ZENER_R2`, `config.h` | Zener-only divider scale; edit the correct TC1/T7 branch |
| `HW_REF25`, `UREF_25`, `config.h` | External reference availability/value; affects supply/reference calculations beyond the Zener tool |
| `BAT_OFFSET`, `config.h` | Battery indication and battery thresholds; does not calibrate the Zener input |

Do not change `UREF_25` or `UREF_VCC` just to make one Zener reading match.
Check the actual reference independently with a suitably accurate meter first.
The project's original manual discusses reference calibration in more detail.

### 4. Rebuild, preserve calibration, and verify

`tests/check_tc1.py` deliberately asserts the board calibration constants.
When intentionally changing `ZENER_R2` (or another asserted board constant),
update the expected value in the appropriate board branch of that file too.
Keep the checks enabled, build the selected target again, and flash with the
same-device EEPROM backup/restore procedure above. No STC reflash is needed
for a divider-scale adjustment.

Repeat the loaded DMM/display comparisons across the voltage range you intend
to use. Save the measurements alongside the settings so you can distinguish
actual hardware calibration from assumptions copied from another tester.

## Credits and licenses

The AVR firmware is Markus Reschke's m-firmware, licensed under
[EUPL 1.2](EUPL-v1.2.txt); see the preserved manual for its history and disclaimer.
TC1 configuration work used
[Kernel-Error/tc1-firmware-update](https://github.com/Kernel-Error/tc1-firmware-update).
The separate T7 STC8G implementation follows the interface described by
[atar-axis/tc1-u4](https://github.com/atar-axis/tc1-u4) and is licensed under
[GPL 3.0 or later](power-controller/stc8g/LICENSE), as marked in its source files.
