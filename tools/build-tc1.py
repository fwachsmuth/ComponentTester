#!/usr/bin/env python3
"""Build the enhanced TC1 profile with the proven fast display transport."""
from pathlib import Path
import subprocess
import sys

subprocess.run([sys.executable, str(Path(__file__).with_name('build-t7.py')),
                '--board', 'TC1', '--fast-display', *sys.argv[1:]], check=True)
