# -*- coding: utf-8 -*-

import argparse
from pathlib import Path
import time
import sys

from nanoporemlv2.signal.signal import Signals
from nanoporemlv2.signal.standards import NONRAW_STANDARDS

#%%

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--standard", choices=NONRAW_STANDARDS.keys(), required=True)
    parser.add_argument("path", type=Path)
    parser.add_argument("-o", "--out", type=Path)
    parser.add_argument("--overwrite", action='store_true')
    args = parser.parse_args()

    #%%

    print('========== signals_to_std_signals.py ==========')
    print(f'Started at time: {time.asctime(time.localtime())}')
    print(f'CWD: {Path.cwd()}')
    print(f'Arguments: {args}')
    print()

    #%%

    if not args.path.exists():
        print('Signals file not found')
        sys.exit(1)

    if args.out is not None:
        if args.out.suffixes[-2:] != ['.stdsignals', '.npz']:
            out_path = args.out.with_suffix(args.out.suffix + '.stdsignals.npz')
        else:
            out_path = args.out
    else:
        if args.path.suffixes[-2:] == ['.rawsignals', '.npz']:
            out_path = args.path.with_name( args.path.name[:-len('.rawsignals.npz')] + '.stdsignals.npz' )
        elif args.path.suffixes[-2:] == ['.signals', '.npz']:
            out_path = args.path.with_name( args.path.name[:-len('.signals.npz')] + '.stdsignals.npz' )
        else:
            out_path = args.path.with_suffix(args.path.suffix + '.stdsignals.npz')
    print(f'Output destination: {out_path}')

    if out_path.is_dir():
        print('Invalid output destination (must not be a directory)')
        sys.exit(1)

    if out_path.exists() and not args.overwrite:
        print('Existing file at output destination and --overwrite not passed')
        sys.exit(1)

    print()

    #%%

    print('Loading signals...')
    try:
        signals = Signals.load(args.path)
    except Exception:
        print('Failed to load from signals file')
        sys.exit(3)
    print('Load signals OK')

    if signals.standard != 'raw':
        print('Signals are not raw')
        sys.exit(4)

    print(f'Standardizing signals to standard {args.standard}...')
    try:
        signals.standardize(args.standard)
    except Exception:
        print(f'Failed to standardize signals') # Most likely cause: Missing pore info
        sys.exit(5) # Potentially also not user error but most likely is user error ^
    print('Standardize signals OK')

    print('Saving now standardized signals...')
    attempt = 1
    base_delay = 15
    max_attempts = 3
    while True:
        try:
            signals.save(out_path, overwrite=True)
            break
        except Exception as e:
            if isinstance(e, (BlockingIOError, PermissionError)):
                if attempt > max_attempts:
                    print(f'Failed to save file and max attempts exceeded')
                    sys.exit(6)
                else:
                    delay = base_delay * attempt
                    print(f'Failed to save file, retrying after {delay} seconds...')
                    time.sleep(delay)
                    attempt += 1
            else:
                print('Non-OS error saving signals')
                sys.exit(102)
    print('Successfully saved signals')

    #%%

    print()
    sys.exit(0)
