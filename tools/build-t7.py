#!/usr/bin/env python3
"""Build TC1/T7 AVR images separately; never program hardware."""
from pathlib import Path
import argparse
import os
import shutil
import subprocess
import sys
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--board', choices=('T7', 'TC1'), default='T7')
parser.add_argument('-j', type=int, default=4, metavar='JOBS')
parser.add_argument('--fast-display', action='store_true', help='build experimental display transport separately')
args = parser.parse_args()
if args.j < 1:
    parser.error('JOBS must be positive')
root = Path(__file__).resolve().parents[1]
profile = args.board.lower() + ('-fast' if args.fast_display else '')
output = root / 'build' / profile
name = f'ComponentTester-{args.board}' + ('-fast-display' if args.fast_display else '')
with tempfile.TemporaryDirectory(prefix=f'component-{profile}-') as directory:
    stage = Path(directory)
    for source in root.iterdir():
        if source.is_file() and (source.suffix in ('.c', '.h', '.S') or source.name == 'Makefile'):
            shutil.copy2(source, stage / source.name)
    for directory_name in ('bitmaps', 'tools', 'tests'):
        shutil.copytree(root / directory_name, stage / directory_name)
    subprocess.run(['sh', 'tools/build-tc1.sh', f'-j{args.j}', f'BOARD={args.board}',
                    f'DISPLAY_FAST={int(args.fast_display)}'],
                   cwd=stage, env={**os.environ, 'TEST_BOARD': 'T7' if args.board == 'T7' else 'TC1_ENHANCED'}, check=True)
    if args.fast_display:
        check = [sys.executable, str(stage / 'tests' / 'check_t7_transport.py')]
        baseline = root / 'build' / 't7' / 'ComponentTester-T7.elf'
        if baseline.exists():
            check += ['--baseline', str(baseline), '--candidate', str(stage / 'ComponentTester')]
        subprocess.run(check, cwd=stage, check=True)
    output.mkdir(parents=True, exist_ok=True)
    # Deliberately export no default EEPROM image: preserve device calibration.
    for source, target in [('ComponentTester.hex', name + '.hex'),
                           ('ComponentTester', name + '.elf'),
                           ('ComponentTester.map', name + '.map')]:
        shutil.copy2(stage / source, output / target)
print(f'{args.board} flash image: {output / (name + ".hex")}')
