"""Compare the production compact font decoder/renderer with original pixels."""
from pathlib import Path
import runpy
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
packer = runpy.run_path(str(ROOT / 'tools' / 'pack-t7-font.py'))
raw, mapping = packer['original_font']()
header, _ = packer['packed_header'](raw, mapping)
assert (ROOT / 'bitmaps' / 'font_8x16_alt_hf_packed.h').read_text() == header
driver = (ROOT / 'ST7735.c').read_text(encoding='latin1')
start = driver.index('#ifdef FONT_ROWS_PACKED\nstatic uint8_t FontIndex')
function = driver.index('void LCD_Char(unsigned char Char)', start)
renderer = driver[start:driver.index('\n}\n', function) + 3]
harness = r'''
#include <stdint.h>
#include <assert.h>
#include <string.h>
#define PROGMEM
#define pgm_read_byte(p) (*(const uint8_t *)(p))
#define pgm_read_word(p) (*(const uint16_t *)(p))
#define FONT_ROWS_PACKED
#define LCD_COLOR
#define FONT_BYTES_X 1
#define FONT_BYTES_Y 16
#define FONT_SIZE_X 8
#define FONT_SIZE_Y 16
#define LCD_CHAR_X 20
#define CMD_MEM_WRITE 0x2c
#define COLOR_BACKGROUND 0
#include "font_8x16_alt_hf_packed.h"
struct {uint8_t CharPos_X, CharPos_Y; uint16_t PenColor;} UI;
uint16_t X_Start, X_End, Y_Start, Y_End;
unsigned emitted, windows, index_expected;
void LCD_CharPos(uint8_t x, uint8_t y) {
  UI.CharPos_X=x; UI.CharPos_Y=y;
  X_Start=(x-1)*8+1; Y_Start=(y-1)*16+2;
}
void LCD_AddressWindow(void) {
  assert(X_Start==153 && X_End==160 && Y_Start==114 && Y_End==129);
  windows++;
}
void LCD_Cmd(uint8_t c) {assert(c==CMD_MEM_WRITE);}
'''
harness += 'const uint8_t Original[]={' + ','.join(map(str, raw)) + '};\n'
harness += 'const uint8_t OriginalMap[]={' + ','.join(map(str, mapping)) + '};\n'
harness += r'''
void LCD_Data2(uint16_t color) {
  assert(emitted<128);
  uint8_t row=Original[index_expected*16+emitted/8];
  assert(color==((row & (1u<<(emitted%8))) ? UI.PenColor : COLOR_BACKGROUND));
  emitted++;
}
'''
harness += renderer
harness += r'''
int main(void) {
  for (unsigned glyph=0; glyph<119; glyph++) {
    uint8_t buffer[18];
    memset(buffer,0xa5,sizeof buffer);
    FontDecode(glyph,buffer+1);
    assert(buffer[0]==0xa5 && buffer[17]==0xa5);
    assert(!memcmp(buffer+1,Original+glyph*16,16));
  }
  for (unsigned ch=0; ch<256; ch++) {
    assert(FontIndex(ch)==OriginalMap[ch]);
    for (unsigned color=0; color<2; color++) {
      emitted=windows=0;
      UI.CharPos_X=20; UI.CharPos_Y=8;
      UI.PenColor=color ? 0xffff : 0x1234;
      index_expected=OriginalMap[ch];
      LCD_Char(ch);
      if (index_expected==255) {
        assert(!emitted && !windows && UI.CharPos_X==20);
      } else {
        assert(emitted==128 && windows==1 && UI.CharPos_X==21);
      }
    }
  }
  emitted=windows=0; UI.CharPos_X=21;
  LCD_Char('A');
  assert(!emitted && !windows && UI.CharPos_X==21);
}
'''
with tempfile.TemporaryDirectory(prefix='t7-font-check-') as directory:
    source = Path(directory) / 'render.c'
    binary = Path(directory) / 'render'
    source.write_text(harness)
    subprocess.run(['cc', '-std=c99', '-Wall', '-Wextra', '-Werror',
                    '-I' + str(ROOT / 'bitmaps'), str(source), '-o', str(binary)], check=True)
    subprocess.run([str(binary)], check=True)
print('Compact font: all 119 glyphs and 256 character mappings match original pixels.')
