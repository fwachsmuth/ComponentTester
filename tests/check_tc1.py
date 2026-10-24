"""Check the effective TC1 hardware configuration and actual icon renderer."""
from pathlib import Path
import os
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
board = os.environ.get('TEST_BOARD', 'TC1')
board_flags = {'T7': ['-DBOARD_T7'], 'TC1_ENHANCED': ['-DBOARD_TC1'], 'TC1': []}[board]

# Check what the AVR compiler actually sees, after config_support.h processing.
source = r'''
#include <avr/io.h>
#include "config.h"
#if F_CPU != 16000000UL || !defined(__AVR_ATmega324P__)
#error Wrong TC1 MCU or clock
#endif
#if !defined(LCD_ST7735) || !defined(SPI_BITBANG) || defined(SPI_HARDWARE)
#error Wrong TC1 display or SPI driver
#endif
#if LCD_RES != PB4 || LCD_DC != PB5 || SPI_MOSI != PB6 || SPI_SCK != PB7
#error Wrong TC1 display wiring
#endif
#if LCD_DOTS_X != 128 || LCD_DOTS_Y != 160 || LCD_OFFSET_X != 2 || LCD_OFFSET_Y != 1 || !defined(LCD_ROTATE) || !defined(LCD_FLIP_X) || defined(LCD_FLIP_Y) || defined(LCD_CS)
#error Wrong TC1 panel geometry or orientation
#endif
#if R_RL_1 != PC0 || R_RH_1 != PC1 || R_RL_2 != PC2 || R_RH_2 != PC3 || R_RL_3 != PC4 || R_RH_3 != PC5
#error Wrong TC1 probe resistor wiring
#endif
#if POWER_CTRL != PD2 || TEST_BUTTON != PD1 || TP_ZENER != PA4 || TP_REF != PA3 || TP_BAT != PA5
#error Wrong TC1 control or ADC wiring
#endif
#if !defined(BAT_DIRECT) || defined(BAT_DIVIDER) || BAT_LOW != 3100 || BAT_WEAK != 3400
#error Wrong TC1 battery settings
#endif
#if defined(BOARD_T7) || defined(BOARD_TC1)
#if !defined(SW_C_VLOSS) || !defined(SW_HFE_CURRENT) || !defined(SW_R_E96_EIA96)
#error Missing additional T7 measurement information
#endif
#if POWER_OFF_TIMEOUT != 60
#error Wrong enhanced profile inactivity timeout
#endif
#ifdef BOARD_T7
#if BAT_OFFSET != 45 || UREF_25 != 2499 || ZENER_R2 != 12000
#error Wrong T7 calibration constants
#endif
#else
#if BAT_OFFSET != 20 || UREF_25 != 2495 || ZENER_R2 != 11750
#error Wrong enhanced TC1 battery correction or reference setting
#endif
#endif
#if !defined(HW_REF25) || !defined(HW_ZENER) || !defined(ZENER_UNSWITCHED) || !defined(ZENER_DIVIDER_CUSTOM) || ZENER_R1 != 100000
#error Wrong reference or Zener configuration
#endif
#if !defined(HW_IR_RECEIVER) || defined(SW_IR_RECEIVER) || IR_DATA != PD3
#error Wrong T7 onboard IR receiver configuration
#endif
_Static_assert(_SFR_MEM_ADDR(IR_PORT) == _SFR_MEM_ADDR(PORTD), "T7 IR port");
_Static_assert(_SFR_MEM_ADDR(IR_DDR) == _SFR_MEM_ADDR(DDRD), "T7 IR direction");
_Static_assert(_SFR_MEM_ADDR(IR_PIN) == _SFR_MEM_ADDR(PIND), "T7 IR input");
#else
#if BAT_OFFSET != 290 || defined(POWER_OFF_TIMEOUT)
#error Changed TC1 battery correction or inactivity timeout
#endif
#if defined(HW_IR_RECEIVER) || !defined(SW_IR_RECEIVER)
#error Changed TC1 external IR receiver configuration
#endif
#if defined(HW_REF25) || defined(HW_ZENER)
#error Changed TC1 optional analog hardware
#endif
#endif
#if !defined(DATA_FLASH) || !defined(UI_AUTOHOLD) || !defined(UI_SHORT_CIRCUIT_MENU)
#error Missing TC1 behavior
#endif
#if !defined(UI_TC1) || !defined(UI_BATTERY_LASTLINE) || !defined(SW_SYMBOLS) || !defined(UI_PROBE_COLORS) || !defined(FONT_8x16_ALT_HF)
#error Missing TC1 graphical layout
#endif
#if defined(SW_PWM_SIMPLE) || defined(SW_PWM_PLUS) || defined(SW_SQUAREWAVE) || defined(SW_SERVO)
#error OC1B is not connected to TC1 probe 2
#endif
#if !defined(UI_MAINMENU_POWERON_BUTTON) || !defined(UI_PREFIX) || !defined(SW_R_E24_5_CC) || !defined(SW_R_TRIMMER) || !defined(SW_MONITOR_RCL) || !defined(SW_DIODE_LED) || !defined(SW_ESR_TOOL) || !defined(SW_REVERSE_HFE) || !defined(SW_CAP_LEAKAGE)
#error Missing requested TC1 tools
#endif
_Static_assert(_SFR_MEM_ADDR(R_PORT) == _SFR_MEM_ADDR(PORTC), "resistor port");
_Static_assert(_SFR_MEM_ADDR(ADC_PORT) == _SFR_MEM_ADDR(PORTA), "ADC port");
_Static_assert(_SFR_MEM_ADDR(POWER_PORT) == _SFR_MEM_ADDR(PORTD), "power port");
_Static_assert(_SFR_MEM_ADDR(BUTTON_PORT) == _SFR_MEM_ADDR(PORTD), "button port");
_Static_assert(_SFR_MEM_ADDR(LCD_PORT) == _SFR_MEM_ADDR(PORTB), "display port");
'''
subprocess.run(['avr-gcc', *board_flags, '-mmcu=atmega324p', '-DF_CPU=16000000UL',
                '-DOSC_STARTUP=16384', '-I.', '-Ibitmaps', '-std=gnu99',
                '-fsyntax-only', '-x', 'c', '-'],
               input=source, text=True, stdout=subprocess.DEVNULL, check=True)

# The old linker can produce an oversized image without reporting an error.
# Validate the actual flash address range as well as Intel HEX checksums.
def flash_extent(hex_text):
    base = end = 0
    for line in hex_text.splitlines():
        record = bytes.fromhex(line.removeprefix(':'))
        assert len(record) == record[0] + 5 and sum(record) % 256 == 0
        address = int.from_bytes(record[1:3], 'big')
        kind, data = record[3], record[4:-1]
        if kind == 0:
            end = max(end, base + address + len(data))
        elif kind == 2:
            base = int.from_bytes(data, 'big') << 4
        elif kind == 4:
            base = int.from_bytes(data, 'big') << 16
    return end

extent = flash_extent((ROOT / 'ComponentTester.hex').read_text())
assert extent <= 32768, f'Firmware exceeds TC1 flash: {extent} > 32768 bytes'
print(f'{board} flash image: {extent}/32768 bytes ({32768-extent} bytes free).')

# Optional symbol tails must retain their original IDs if re-enabled later.
for extended, count in [(False, 15), (True, 18)]:
    symbols = '#include "config.h"\n#include "common.h"\n'
    if extended:
        symbols += '#define UI_ZENER_DIODE\n'
    symbols += '#include "bitmaps/symbols_30x32_hf.h"\n'
    symbols += f'_Static_assert(sizeof(SymbolData) == {count}*128, "symbol count");\n'
    symbols += f'_Static_assert(sizeof(PinTable) == {count}*3, "pin table count");\n'
    subprocess.run(['avr-gcc', '-mmcu=atmega324p', '-DF_CPU=16000000UL',
                    '-DOSC_STARTUP=16384', '-I.', '-Ibitmaps', '-std=gnu99',
                    '-Os', '-fsyntax-only', '-x', 'c', '-'],
                   input=symbols, text=True, stdout=subprocess.DEVNULL, check=True)

# Compile the production renderer against a mocked LCD transport. This checks
# the emitted pixels, physical bounds including panel offsets, and UI state.
driver = (ROOT / 'ST7735.c').read_text(encoding='latin1')
start = driver.index('static const uint16_t TC1PassiveIcons')
end = driver.index('\n#endif', start)
renderer = driver[start:end]
harness = r'''
#include <stdint.h>
#include <assert.h>
#define PROGMEM
#define pgm_read_word(p) (*(p))
#define LCD_CHAR_X 20
#define LCD_CHAR_Y 8
#define FONT_SIZE_X 8
#define FONT_SIZE_Y 16
#define COLOR_SYMBOL 0xffff
#define COLOR_BACKGROUND 0
#define CMD_MEM_WRITE 0x2c
struct { uint8_t CharPos_X, CharPos_Y; } UI;
uint16_t X_Start, X_End, Y_Start, Y_End;
unsigned count, marks, windows;
uint16_t pixels[1024];
void LCD_CharPos(uint8_t x, uint8_t y) {
  UI.CharPos_X=x; UI.CharPos_Y=y;
  marks |= 1u << (y-1);
  X_Start=(x-1)*8+1; Y_Start=(y-1)*16+2;
}
void LCD_AddressWindow(void) {
  assert(X_Start==129 && X_End==160 && Y_Start==2 && Y_End==33);
  windows++;
}
void LCD_Cmd(uint8_t c) { assert(c==CMD_MEM_WRITE); }
void LCD_Data2(uint16_t c) { assert(count<1024); pixels[count++]=c; }
'''
harness += renderer
harness += r'''
int main(void) {
  for (unsigned id=0; id<2; id++) {
    count=marks=windows=0; UI.CharPos_X=12; UI.CharPos_Y=6;
    LCD_TC1Passive(id);
    assert(count==1024 && windows==1 && (marks&3)==3);
    assert(UI.CharPos_X==12 && UI.CharPos_Y==6);
    unsigned lit=0;
    for (unsigned y=0; y<32; y++) for (unsigned x=0; x<32; x++) {
      uint16_t c=pixels[y*32+x];
      assert(c==0 || c==COLOR_SYMBOL);
      assert(c==pixels[(y/2*2)*32+(x/2*2)]);
      if (c) lit++;
    }
    assert(lit>80 && lit<512);
  }
  count=windows=0;
  LCD_TC1Passive(2);
  assert(count==0 && windows==0 && UI.CharPos_X==12 && UI.CharPos_Y==6);
}
'''
with tempfile.TemporaryDirectory(prefix='tc1-check-') as folder:
    c_file = Path(folder) / 'render.c'
    exe = Path(folder) / 'render'
    c_file.write_text(harness)
    subprocess.run(['cc', '-std=c99', '-Wall', '-Wextra', '-Werror', str(c_file),
                    '-o', str(exe)], check=True)
    subprocess.run([str(exe)], check=True)

if board in ('T7', 'TC1_ENHANCED'):
    import sys
    subprocess.run([sys.executable, str(ROOT / 'tests' / 'check_t7_symbols.py')], check=True)
    subprocess.run([sys.executable, str(ROOT / 'tests' / 'check_t7_font.py')], check=True)

print(f'{board} configuration and icon renderer checks passed.')
