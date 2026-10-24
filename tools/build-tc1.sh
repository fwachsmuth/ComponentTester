#!/bin/sh
# Build only; never programs the tester or changes fuses.
set -eu
cd "$(dirname "$0")/.."
if ! command -v avr-gcc >/dev/null 2>&1; then
    avr_bin=${ARDUINO_AVR_BIN:-/Applications/Arduino.app/Contents/Java/hardware/tools/avr/bin}
    if [ ! -x "$avr_bin/avr-gcc" ]; then
        echo 'avr-gcc is missing. Add an AVR toolchain to PATH or set ARDUINO_AVR_BIN.' >&2
        exit 1
    fi
    PATH="$avr_bin:$PATH"
    export PATH
fi
# Recompile to avoid reusing objects built for a different MCU or clock.
make -B "$@"
python3 tests/check_tc1.py
