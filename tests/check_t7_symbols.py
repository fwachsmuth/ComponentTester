"""Check the actual packed LCD_Symbol renderer against every original pixel."""
from pathlib import Path
import runpy
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
packer = runpy.run_path(str(ROOT / 'tools' / 'pack-t7-symbols.py'))
raw = packer['raw_symbols']()
header, _ = packer['packed_header'](raw)
assert (ROOT / 'bitmaps' / 'symbols_30x32_hf_packed.h').read_text() == header
driver = (ROOT / 'ST7735.c').read_text(encoding='latin1')
start = driver.index('void LCD_Symbol(uint8_t ID)')
renderer = driver[start:driver.index('\n}\n', start) + 3]
harness = r'''
#include <stdint.h>
#include <assert.h>
#define PROGMEM
#define pgm_read_byte(p) (*(const uint8_t *)(p))
#define SYMBOL_ROWS_PACKED
#define LCD_COLOR
#define SYMBOL_BYTES_Y 32
#define SYMBOL_BYTES_X 4
#define SYMBOL_SIZE_X 30
#define SYMBOL_SIZE_Y 32
#define SYMBOL_RESIZE resize
#define LCD_SYMBOL_CHAR_Y ((32*resize+15)/16)
#define CMD_MEM_WRITE 0x2c
#define COLOR_BACKGROUND 0
#include "symbols_30x32_hf_packed.h"
struct {uint8_t CharPos_X, CharPos_Y, SymbolPos_Y; uint16_t PenColor;} UI;
uint16_t X_Start, X_End, Y_Start, Y_End;
unsigned resize, id, emitted, windows;
void LCD_CharPos(uint8_t x, uint8_t y) {
  UI.CharPos_X=x; UI.CharPos_Y=y;
  X_Start=(x-1)*8+1; Y_Start=(y-1)*16+2;
}
void LCD_AddressWindow(void) {
  assert(X_Start==9 && Y_Start==18);
  assert(X_End==X_Start+30*resize-1 && Y_End==Y_Start+32*resize-1);
  windows++;
}
void LCD_Cmd(uint8_t c) {assert(c==CMD_MEM_WRITE);}
'''
harness += 'const uint8_t Original[]={' + ','.join(map(str, raw)) + '};\n'
harness += r'''
void LCD_Data2(uint16_t color) {
  assert(emitted < 30*32*resize*resize);
  unsigned x=(emitted%(30*resize))/resize;
  unsigned y=(emitted/(30*resize))/resize;
  uint8_t bits=Original[id*128+y*4+x/8];
  assert(color==((bits & (1u<<(x%8))) ? UI.PenColor : COLOR_BACKGROUND));
  emitted++;
}
'''
harness += renderer
harness += r'''
int main(void) {
  for (resize=1; resize<=2; resize++)
    for (id=0; id<15; id++)
      for (unsigned color=0; color<2; color++) {
        emitted=windows=0;
        UI.CharPos_X=UI.CharPos_Y=UI.SymbolPos_Y=2;
        UI.PenColor=color ? 0xffff : 0x1234;
        LCD_Symbol(id);
        assert(windows==1 && emitted==30*32*resize*resize);
      }
}
'''
with tempfile.TemporaryDirectory(prefix='t7-symbol-check-') as directory:
    source = Path(directory) / 'render.c'
    binary = Path(directory) / 'render'
    source.write_text(harness)
    subprocess.run(['cc', '-std=c99', '-Wall', '-Wextra', '-Werror',
                    '-I' + str(ROOT / 'bitmaps'), str(source), '-o', str(binary)], check=True)
    subprocess.run([str(binary)], check=True)
print('Packed symbol renderer: all 15 symbols match original pixels at 1x and 2x.')
