"""Execute compiled AVR display transports; compare wire bits and cycle counts.

This models only the instruction subset emitted by these isolated routines,
not a complete MCU. Unknown instructions fail; interrupt/electrical effects
are not modeled. Host renderer tests separately check image content.
"""
from pathlib import Path
import argparse
import re
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
compiler = shutil.which('avr-gcc') or '/Applications/Arduino.app/Contents/Java/hardware/tools/avr/bin/avr-gcc'
objdump = str(Path(compiler).with_name('avr-objdump'))


def function(path, signature):
    source = path.read_text(encoding='latin1')
    start = source.index(signature)
    return source[start:source.index('\n}\n', start)+3]


def compile_transport(folder, fast):
    prefix = '''#include <avr/io.h>
#include <stdint.h>
#define BOARD_T7
#define SPI_BITBANG
#define SPI_PORT PORTB
#define SPI_MOSI PB6
#define SPI_SCK PB7
#define LCD_PORT PORTB
#define LCD_DC PB5
#define COLOR_BACKGROUND 0
'''
    if fast:
        source = prefix + '#include "ST7735_fast.h"\n'
        source += 'void ProbeFill(uint16_t n) {LCD_BackgroundRow(n);}\n'
    else:
        source = prefix + function(ROOT/'SPI.c', 'void SPI_Write_Byte(uint8_t Byte)')
        source += function(ROOT/'ST7735.c', 'void LCD_Data2(uint16_t Data)')
        source += 'void ProbeFill(uint16_t n) {while(n--) LCD_Data2(0);}\n'
    cfile = folder / ('fast.c' if fast else 'baseline.c')
    elf = cfile.with_suffix('.elf')
    cfile.write_text(source)
    subprocess.run([compiler, '-mmcu=atmega324p', '-Os', '-std=gnu99',
                    '-mcall-prologues', '-I'+str(ROOT), '-nostartfiles',
                    '-Wl,-e,LCD_Data2', str(cfile), '-o', str(elf)], check=True)
    disassembly = subprocess.check_output([objdump, '-d', str(elf)], text=True)
    return parse(disassembly)


def parse(disassembly):
    labels, instructions = {}, {}
    for line in disassembly.splitlines():
        label = re.match(r'([0-9a-f]+) <([^>]+)>:', line)
        if label:
            labels[label[2]] = int(label[1], 16)
        instruction = re.match(r'\s*([0-9a-f]+):\s+((?:[0-9a-f]{2}\s+)+)\s*([a-z]+)\s*(.*)', line)
        if instruction:
            address = int(instruction[1], 16)
            size = len(instruction[2].split())
            operands, _, comment = instruction[4].partition(';')
            target = re.search(r'0x([0-9a-f]+)', comment)
            instructions[address] = (instruction[3], operands.strip(), address+size,
                                     int(target[1], 16) if target else None)
    return labels, instructions


def execute(program, entry, value, initial_port=0x1b, edges=None):
    labels, code = program
    r = [0]*32
    r[24], r[25] = value & 255, value >> 8
    port, cycles, c, z, t = initial_port, 0, 0, 0, 0
    pc = labels[entry]
    calls, stack, bits = [], [], []

    def reg(s): return int(s[1:])
    def word(n): return r[n] | r[n+1] << 8
    def setword(n, value): r[n], r[n+1] = value & 255, value >> 8 & 255
    def write(address, value):
        nonlocal port
        old = port
        if address == 3: port ^= value  # PINB toggles PORTB
        elif address == 5: port = value
        else: raise AssertionError(('unexpected IO write', address))
        assert (port & 31) == (initial_port & 31), 'Changed non-display port bits'
        if edges is not None and (old ^ port) & 128:
            edges.append((cycles, bool(port & 128)))
        if not old & 128 and port & 128:
            assert port & 32, 'D/C must be high at every data clock'
            bits.append((port >> 6) & 1)

    steps = 0
    while True:
        steps += 1
        assert steps < 200000, 'Execution did not terminate'
        op, operands, nextpc, target = code[pc]
        a = [part.strip() for part in operands.split(',')]
        cost, jump = 1, nextpc
        if op == 'ldi': r[reg(a[0])] = int(a[1], 0)
        elif op == 'mov': r[reg(a[0])] = r[reg(a[1])]
        elif op == 'movw': setword(reg(a[0]), word(reg(a[1])))
        elif op == 'in':
            assert int(a[1], 0) == 5
            r[reg(a[0])] = port
        elif op == 'out': write(int(a[0], 0), r[reg(a[1])])
        elif op in ('sbi', 'cbi'):
            address, bit = int(a[0], 0), int(a[1], 0)
            assert address == 5
            write(address, port | (1 << bit) if op == 'sbi' else port & ~(1 << bit))
            cost = 2
        elif op in ('andi', 'ori', 'and', 'or', 'eor'):
            n = reg(a[0]); b = int(a[1], 0) if op.endswith('i') else r[reg(a[1])]
            r[n] = r[n] & b if op.startswith('and') else r[n] ^ b if op == 'eor' else r[n] | b
            z = r[n] == 0
        elif op in ('add', 'adc'):
            n = reg(a[0]); value = r[n] + r[reg(a[1])] + (c if op == 'adc' else 0)
            r[n], c, z = value & 255, value > 255, (value & 255) == 0
        elif op in ('subi', 'sbci'):
            n = reg(a[0]); value = r[n] - int(a[1], 0) - (c if op == 'sbci' else 0)
            r[n], c, z = value & 255, value < 0, (value & 255) == 0
        elif op in ('sbiw', 'adiw'):
            n = reg(a[0]); value = word(n) + int(a[1], 0) * (-1 if op == 'sbiw' else 1)
            setword(n, value); c, z, cost = value < 0 or value > 65535, (value & 65535) == 0, 2
        elif op == 'dec':
            n = reg(a[0]); r[n] = (r[n]-1) & 255; z = r[n] == 0
        elif op == 'bst': t = (r[reg(a[0])] >> int(a[1], 0)) & 1
        elif op == 'bld':
            n, bit = reg(a[0]), int(a[1], 0); r[n] = (r[n] & ~(1 << bit)) | t << bit
        elif op in ('sbrs', 'sbrc'):
            bit = (r[reg(a[0])] >> int(a[1], 0)) & 1
            if bool(bit) == (op == 'sbrs'):
                jump = code[nextpc][2]; cost = 1 + (jump-nextpc)//2
        elif op in ('brne', 'breq'):
            if bool(z) == (op == 'breq'): jump, cost = target, 2
        elif op in ('brcc', 'brcs'):
            if bool(c) == (op == 'brcs'): jump, cost = target, 2
        elif op in ('rjmp', 'jmp'): jump, cost = target, 2 if op == 'rjmp' else 3
        elif op in ('rcall', 'call'):
            calls.append(nextpc); jump, cost = target, 3 if op == 'rcall' else 4
        elif op == 'ret':
            cycles += 4
            if not calls: break
            pc = calls.pop(); continue
        elif op == 'push': stack.append(r[reg(a[0])]); cost = 2
        elif op == 'pop': r[reg(a[0])] = stack.pop(); cost = 2
        elif op == 'nop': pass
        else: raise AssertionError(('unsupported instruction', op, operands))
        pc, cycles = jump, cycles + cost
    assert not stack and not port & 128, 'Unbalanced stack or SCK not idle low'
    return bits, cycles


with tempfile.TemporaryDirectory(prefix='t7-transport-check-') as directory:
    folder = Path(directory)
    baseline, fast = (compile_transport(folder, mode) for mode in (False, True))
    oldcycles = newcycles = 0
    values = [0, 65535] + [1 << bit for bit in range(16)]
    values += [(value << 8) | (value ^ 0xa5) for value in range(256)]
    for value in values:
        expected = [(value >> bit) & 1 for bit in range(15, -1, -1)]
        for port in (0x00, 0x1b, 0x3f, 0x5b):
            old, oc = execute(baseline, 'LCD_Data2', value, port)
            new, nc = execute(fast, 'LCD_Data2', value, port)
            assert old == new == expected
        oldcycles += oc; newcycles += nc
    print(f'Word transfer: {oldcycles/len(values):.1f} -> {newcycles/len(values):.1f} CPU cycles on average.')
    reference_edges = []
    execute(fast, 'LCD_Data2', 0, edges=reference_edges)
    minimum = {state: min(b[0]-a[0] for a,b in zip(reference_edges,reference_edges[1:])
                          if a[1] == state) for state in (False,True)}
    print(f'Pixel clock minimum high/low: {minimum[True]}/{minimum[False]} CPU cycles.')
    for count in (0, 1, 2, 7, 31, 160):
        old, oc = execute(baseline, 'ProbeFill', count)
        fill_edges = []
        new, nc = execute(fast, 'ProbeFill', count, edges=fill_edges)
        assert old == new == [0]*(16*count)
        for a,b in zip(fill_edges,fill_edges[1:]):
            assert b[0]-a[0] >= minimum[a[1]], 'Fill clock pulse shorter than pixel writer'
        if count:
            assert nc < oc, 'Background fill did not improve'
        if count == 160:
            print(f'160-pixel row fill: {oc} -> {nc} cycles; {oc/16e3:.3f} -> {nc/16e3:.3f} ms at 16 MHz.')
    print('Transport checks passed: wire bits, MSB order, D/C, idle clock and preserved GPIO bits.')

    # Compare the complete line-clearing paths, including partial lines and
    # already-empty lines. The bulk helper emits the same pixel stream.
    clear = function(ROOT/'ST7735.c', 'void LCD_ClearLine(uint8_t Line)')
    harness = r'''
#include <stdint.h>
#include <assert.h>
#include <string.h>
#define FONT_SIZE_Y 16
#define LCD_PIXELS_X 160
#define LCD_PIXELS_Y 128
#define LCD_SHIFT_X 1
#define LCD_SHIFT_Y 2
#define COLOR_BACKGROUND 0
#define CMD_MEM_WRITE 0x2c
#define wdt_reset() ((void)0)
struct {uint8_t CharPos_X,CharPos_Y;} UI;
uint16_t X_Start,X_End,Y_Start,Y_End,LineFlags;
uint16_t events[3000][5], saved[3000][5];
unsigned count;
void LCD_CharPos(uint8_t x,uint8_t y) {
  UI.CharPos_X=x; UI.CharPos_Y=y;
  X_Start=1+(x-1)*8; Y_Start=2+(y-1)*16;
}
void LCD_AddressWindow(void) {
  events[count][0]=1; events[count][1]=X_Start; events[count][2]=X_End;
  events[count][3]=Y_Start; events[count++][4]=Y_End;
}
void LCD_Cmd(uint8_t cmd) {events[count][0]=2; events[count++][1]=cmd;}
void LCD_Data2(uint16_t data) {events[count][0]=3; events[count++][1]=data;}
void LCD_BackgroundRow(uint16_t pixels) {while(pixels--) LCD_Data2(0);}
'''
    harness += clear.replace('void LCD_ClearLine(', 'void BaselineClear(')
    harness += '\n#define T7_FAST_DISPLAY\n'
    harness += clear.replace('void LCD_ClearLine(', 'void FastClear(')
    harness += r'''
int main(void) {
  for(unsigned line=0;line<=8;line++) for(unsigned pos=1;pos<=21;pos++)
    for(unsigned empty=0;empty<2;empty++) {
      memset(events,0,sizeof events); count=0;
      UI.CharPos_X=pos; UI.CharPos_Y=8; LineFlags=empty ? 0 : 65535;
      BaselineClear(line);
      unsigned oldcount=count; uint16_t oldflags=LineFlags;
      unsigned oldx=UI.CharPos_X,oldy=UI.CharPos_Y;
      memcpy(saved,events,sizeof events);
      memset(events,0,sizeof events); count=0;
      UI.CharPos_X=pos; UI.CharPos_Y=8; LineFlags=empty ? 0 : 65535;
      FastClear(line);
      assert(count==oldcount && LineFlags==oldflags);
      assert(UI.CharPos_X==oldx && UI.CharPos_Y==oldy);
      assert(!memcmp(saved,events,sizeof events));
    }
}
'''
    source = folder / 'clear.c'
    source.write_text(harness)
    binary = folder / 'clear'
    subprocess.run(['cc', '-std=c99', '-Wall', '-Wextra', '-Werror',
                    str(source), '-o', str(binary)], check=True)
    subprocess.run([str(binary)], check=True)
    print('Line clearing matches: address windows, pixel streams, partial/empty lines and UI state.')

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--baseline', type=Path)
parser.add_argument('--candidate', type=Path)
args = parser.parse_args()
if args.baseline and args.candidate:
    programs = [parse(subprocess.check_output([objdump, '-d', str(path)], text=True))
                for path in (args.baseline, args.candidate)]
    totals = [0, 0]
    for value in values:
        expected = [(value >> bit) & 1 for bit in range(15, -1, -1)]
        for index, program in enumerate(programs):
            bits, cycles = execute(program, 'LCD_Data2', value)
            assert bits == expected
            totals[index] += cycles
    assert totals[1] < totals[0], 'Candidate linked word writer did not improve'
    print('Actual linked word routines:',
          ' -> '.join(f'{total/len(values):.1f}' for total in totals), 'CPU cycles on average.')
