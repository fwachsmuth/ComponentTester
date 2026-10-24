# Experimental T7 display transport

Build with `python3 tools/build-t7.py --fast-display -j4`.

Output: `build/t7-fast/ComponentTester-T7-fast-display.hex`.
The normal `build/t7/ComponentTester-T7.hex` remains the working baseline.
No hardware is programmed by the build. Preserve calibration EEPROM and fuses
when updating AVR flash; U5 needs no change.

The experiment retains all tools, fonts, symbols, colors, layout and measurement
code. `T7_FAST_DISPLAY` selects a specialized mode-0 16-bit writer for the verified
PB5 D/C, PB6 MOSI, PB7 clock wiring. It preserves PB0..PB4 and leaves clock low.
Writing PINB with only bit 7 set toggles only the clock output, as documented in
the ATmega324PA datasheet section 14.2.2. The revised background-row routine
repeats the same 16-bit word writer used for text and symbols, including its
clock timing. No framebuffer or interrupt masking is used.
The display must remain the sole active writer of PORTB while transmitting.

The revised candidate occupies 32,744/32,768 bytes: 28 bytes more than the baseline,
with 24 bytes free. Static RAM is unchanged at 252 bytes. It is faster in the
instruction model, but is not smaller. Further additions require size recovery.

## Verification and timing limits

Configuration, actual font/symbol pixel tests and HEX bounds/checksums pass.
The baseline T7 is rebuilt separately and checked against the working HEX;
the default TC1 profile is also rebuilt and checked.

Run:

```sh
python3 tests/check_t7_transport.py \
  --baseline build/t7/ComponentTester-T7.elf \
  --candidate build/t7-fast/ComponentTester-T7-fast-display.elf
```

This executes the compiled AVR transport instruction subset in a small model. It compares wire
bits for all byte values in both positions plus single-bit patterns, validates
MSB order, D/C, clock return and preservation of unrelated GPIO bits. Unknown
instructions fail. It also compares complete line-clearing address windows,
pixel streams and UI state for full, partial and already-empty lines.

| Routine | Baseline | Experiment |
| --- | ---: | ---: |
| Actual linked word writer, mean CPU cycles over test patterns | 248.2 | 170.0 |
| Isolated compiled 160-pixel background span, CPU cycles | 44,976 | 29,136 |
| Same isolated span, calculated time at 16 MHz | 2.811 ms | 1.821 ms |

Thus the linked word writer uses about 31% fewer cycles; the isolated background
span uses about 35% fewer cycles. These are instruction-derived numbers,
not observed screen timings or a claim that component testing is faster. The
model excludes interrupts and electrical effects. The controller initialization
waits, decoding, layout, address commands and measurement algorithms still cost
time. Physical timing and image integrity require hardware verification.

## R1 hardware feedback and revised clearing

The user reported much faster drawing but failed screen erasure with R1.
Its separate clock-only fill emitted low phases as short as one CPU cycle
(62.5 ns). The logical stream tests passed, but did not establish that the
actual panel and board accepted those pulse widths. Electrical timing is a
likely explanation, not a confirmed diagnosis from a scope capture.

R2 removes the clock-only burst and uses the word writer for all background
pixels. The model now checks that no fill high/low phase is shorter than that
writer's minimum: 3/7 CPU cycles (187.5/437.5 ns at 16 MHz). The revised build
still needs hardware confirmation of erasure. The faulty initial image is
retained only for diagnosis as
`build/t7-fast/ComponentTester-T7-fast-r1-fill-fails.hex`; do not use it as the
working baseline.

## Hardware comparison

1. First keep a baseline capture on the T7. With a 10x probe, connect scope
   ground to battery negative and probe **PB7, ATmega physical pin 3** (LCD clock).
   Optional second channel: **PB5, physical pin 1**, for D/C.
2. Perform a repeatable display operation, such as opening the same menu page.
   Start around 10 ms/div to locate its groups of transfers; zoom in to compare
   individual word writes or a constant-background fill burst. Measure the same
   first-to-last-clock span in both versions. Do not include the component-test
   interval when assessing display speed.
3. Flash the experimental AVR image with calibration EEPROM preserved and repeat
   on the same T7. This avoids board/controller differences. Your TC1 can provide
   a useful side-by-side visual comparison while retaining its own firmware;
   do not cross-flash the T7 hardware profile to make that comparison.
4. Check menus, battery icons, colored resistor bands, semiconductor symbols,
   long/paginated results, clearing and wake/restart for missing or corrupted
   pixels. Confirm that the improvement is visible in normal use.

To revert, restore only the normal T7 flash image using the same EEPROM-preserving
procedure. The known-good baseline has not been replaced by this experiment.
