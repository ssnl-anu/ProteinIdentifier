# -*- coding: utf-8 -*-

import argparse
from pathlib import Path
import time
import sys

from nanoporemlv2.eventextraction.events import Events

#%%

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path)
    parser.add_argument("-o", "--out", type=Path)
    parser.add_argument("--overwrite", action='store_true')
    args = parser.parse_args()

    #%%

    print('========== events_to_signals.py ==========')
    print(f'Started at time: {time.asctime(time.localtime())}')
    print(f'CWD: {Path.cwd()}')
    print(f'Arguments: {args}')
    print()

    #%%

    if not args.path.exists():
        print('Events file not found')
        sys.exit(1)

    if args.out is not None:
        if args.out.suffixes[-2:] != ['.rawsignals', '.npz']:
            out_path = args.out.with_suffix(args.out.suffix + '.rawsignals.npz')
        else:
            out_path = args.out
    else:
        if args.path.suffixes[-2:] == ['.events', '.npz']:
            out_path = args.path.with_name( args.path.name[:-len('.events.npz')] + '.rawsignals.npz' )
        else:
            out_path = args.path.with_suffix(args.path.suffix + '.rawsignals.npz')
    print(f'Output destination: {out_path}')

    if out_path.is_dir():
        print('Invalid output destination (must not be a directory)')
        sys.exit(1)

    if out_path.exists() and not args.overwrite:
        print('Existing file at output destination and --overwrite not passed')
        sys.exit(1)

    print()

    #%%

    print('Loading events...')
    try:
        events = Events.load(args.path)
    except Exception:
        print('Failed to load from events file')
        sys.exit(3)
    print('Load events OK')

    print('Extracting signals from events...')
    try:
        signals = events.to_signals()
    except Exception:
        print('Failed to extract signals from events')
        sys.exit(101)
    print('Extract signals OK')

    print('Saving signals...')
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
                    sys.exit(4)
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
