# -*- coding: utf-8 -*-

import argparse
from pathlib import Path
import time
import sys

from warnings import warn

from nanoporemlv2.signal.signal import Signals
from nanoporemlv2.featureeng.schemes import SCHEMES
from nanoporemlv2.featureeng.datasetio import make_dataset, gen_dataset_meta, save_dataset

#%%

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--scheme", choices=SCHEMES.keys(), required=True)
    parser.add_argument("path", type=Path)
    parser.add_argument("-o", "--out", type=Path)
    parser.add_argument("--overwrite", action='store_true')
    args = parser.parse_args()

    #%%

    print('========== make_dataset.py ==========')
    print(f'Started at time: {time.asctime(time.localtime())}')
    print(f'CWD: {Path.cwd()}')
    print(f'Arguments: {args}')
    print()

    #%%

    if not args.path.exists():
        print('Signals file not found')
        sys.exit(1)

    if args.out is not None:
        if args.out.suffixes[-2:] != ['.dataset', '.npz']:
            out_path = args.out.with_suffix(args.out.suffix + '.dataset.npz')
        else:
            out_path = args.out
    else:
        if args.path.suffixes[-2:] == ['.stdsignals', '.npz']:
            out_path = args.path.with_name( args.path.name[:-len('.stdsignals.npz')] + '.dataset.npz' )
        elif args.path.suffixes[-2:] == ['.rawsignals', '.npz']:
            out_path = args.path.with_name( args.path.name[:-len('.rawsignals.npz')] + '.dataset.npz' )
        elif args.path.suffixes[-2:] == ['.signals', '.npz']:
            out_path = args.path.with_name( args.path.name[:-len('.signals.npz')] + '.dataset.npz' )
        else:
            out_path = args.path.with_suffix(args.path.suffix + '.dataset.npz')
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

    if signals.standard is None:
        warn('Signal standardization status and standard unknown')
    if signals.standard == 'raw':
        warn('Signals are raw')

    try:
        meta = gen_dataset_meta(signals)
    except Exception:
        print('Error generating meta from signals')
        sys.exit(101)

    print(f'Making dataset using scheme {args.scheme}...')
    try:
        dataset = make_dataset(signals, args.scheme)
    except Exception:
        print(f'Failed to make dataset')
        sys.exit(4) # Potentially also not user error but most likely is user error ^
    print('Make dataset OK')

    print('Saving dataset...')
    attempt = 1
    base_delay = 15
    max_attempts = 3
    while True:
        try:
            save_dataset(
                out_path,
                *dataset,
                scheme=args.scheme,
                standard=signals.standard,
                meta=meta,
                overwrite=True
                )
            break
        except Exception as e:
            if isinstance(e, (BlockingIOError, PermissionError)):
                if attempt > max_attempts:
                    print(f'Failed to save file and max attempts exceeded')
                    sys.exit(5)
                else:
                    delay = base_delay * attempt
                    print(f'Failed to save file, retrying after {delay} seconds...')
                    time.sleep(delay)
                    attempt += 1
            else:
                print('Non-OS error saving datset')
                sys.exit(102)
    print('Successfully saved dataset')

    #%%

    print()
    sys.exit(0)
