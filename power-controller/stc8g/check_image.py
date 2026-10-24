"""Verify linked vectors/registers, standby instructions and final HEX images."""
from pathlib import Path
import re

assembly = (Path('build') / 'main-r2.asm').read_text()
# Strip comments: references to the old STOP design must not count as code.
code = '\n'.join(line.split(';', 1)[0] for line in assembly.splitlines())
assert re.search(r'orl\s+_PCON,\s*#0x01\b', code), 'Missing timer-driven IDLE loop'
assert not re.search(r'orl\s+_PCON,\s*#0x0[23]\b', code), 'Unexpected STOP instruction'
assert '_standby:' not in code and '_int2_isr:' not in code
assert re.search(r'ljmp\s+_timer0_isr\b', code), 'Missing Timer0 interrupt vector'
assert not re.search(r'mov\s+dptr,\s*#0xfe0[01]\b', code, re.I), 'Overwrites programmer clock setup'
assert '_CLKDIV' not in code, 'Unexpected STC15 clock register'

base = end = 0
for line in (Path('build') / 't7-stc8g-power-r2-idle.hex').read_text().splitlines():
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
assert 0 < end <= 8192, f'Unexpected code address extent: {end}'
print(f'R2: IDLE standby, Timer0 vector and preserved clock setup passed; {end}/8192 code bytes.')

# The STOP variant must consume the wake request before restarting Timer0.
r3 = (Path('build') / 'main-r3.asm').read_text()
r3 = '\n'.join(line.split(';', 1)[0] for line in r3.splitlines())
assert not re.search(r'mov\s+dptr,\s*#0xfe0[01]\b', r3, re.I)
assert '_CLKDIV' not in r3
assert re.search(r'ljmp\s+_int2_isr\b', r3)
assert re.search(r'setb\s+_EA\s+orl\s+_PCON,\s*#0x02\b', r3)
wake = r3.split('_standby:', 1)[1].split('_main:', 1)[0]
clear = re.search(r'mov\s+_sleep_ready,\s*#0x00', wake)
assert clear and clear.start() < wake.index('lcall\t_timer_restart')
assert re.search(r'clr\s+_ET0\b', wake) and re.search(r'clr\s+_TF0\b', wake)
assert wake.index('clr\t_ET0') < wake.index('orl _PCON')
assert wake.index('lcall\t_timer_restart') < wake.index('setb\t_ET0')
base = end = 0
image = {}
for line in (Path('build') / 't7-stc8g-power-r3-stop.hex').read_text().splitlines():
    record = bytes.fromhex(line.removeprefix(':'))
    assert len(record) == record[0] + 5 and sum(record) % 256 == 0
    address = int.from_bytes(record[1:3], 'big')
    kind, data = record[3], record[4:-1]
    if kind == 0:
        end = max(end, base + address + len(data))
        for offset, byte in enumerate(data):
            image[base + address + offset] = byte
    elif kind == 2:
        base = int.from_bytes(data, 'big') << 4
    elif kind == 4:
        base = int.from_bytes(data, 'big') << 16
assert 0 < end <= 8192
symbols = {
    name: int(address, 16)
    for address, name in re.findall(r'^\s*(?:C:\s*)?([0-9A-Fa-f]{8})\s+(\w+)\s',
                                   (Path('build') / 't7-stc8g-power-r3-stop.map').read_text(), re.M)
}
# Verify actual HEX opcodes and destinations, not just compiler assembly text.
for vector, handler in [(0, '__sdcc_gsinit_startup'), (0x0b, '_timer0_isr'), (0x53, '_int2_isr')]:
    assert image[vector] == 0x02, f'Missing LJMP at vector {vector:#x}'
    assert (image[vector+1] << 8 | image[vector+2]) == symbols[handler]
for register, address in {
    '_AUXR': 0x8e, '_INTCLKO': 0x8f,
    '_P3M1': 0xb1, '_P3M0': 0xb2, '_P5M1': 0xc9, '_P5M0': 0xca,
    '_AUXINTIF': 0xef, '_BUTTON': 0xcc, '_BOOST': 0xcd,
    '_AVR_BUTTON': 0xb2, '_AVR_ONLINE': 0xb3,
}.items():
    assert symbols[register] == address, register
assert 0x21 <= symbols['__start__stack'] < 0x80
print(f'R3: linked vectors/registers, STOP/wake ordering and HEX checks passed; {end}/8192 code bytes.')
