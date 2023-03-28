# -*- coding: utf-8 -*-

import argparse
from pathlib import Path
import time
import sys

from nanoporemlv2.dataloaders import DATALOADERS

from nanoporemlv2.eventextraction.pipeline import EventExtractionPipeline, Settings
from nanoporemlv2.eventextraction.events import Events

#%%

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--format", choices=DATALOADERS.keys(), required=True)
    parser.add_argument("path", type=Path)
    parser.add_argument("--settings", type=Path)
    parser.add_argument("-o", "--out", type=Path)
    parser.add_argument("--overwrite", action='store_true')
    args = parser.parse_args()

    #%%

    print('========== run_pipeline.py ==========')
    print(f'Started at time: {time.asctime(time.localtime())}')
    print(f'CWD: {Path.cwd()}')
    print(f'Arguments: {args}')
    print()

    #%%

    Fmt = DATALOADERS[args.format]

    #%%

    if not args.path.exists():
        print('Data not found')
        sys.exit(1)

    if args.settings is not None:
        settings_path = args.settings
    else:
        settings_path = args.path.with_suffix('.json')
    print(f'Settings file location: {settings_path}')

    if not settings_path.is_file():
        print('Settings file not found')
        sys.exit(1)

    if args.out is not None:
        if args.out.suffixes[-2:] != ['.events', '.npz']:
            out_path = args.out.with_suffix(args.out.suffix + '.events.npz')
        else:
            out_path = args.out
    else:
        out_path = args.path.with_suffix('.events.npz')
    print(f'Output destination: {out_path}')

    if out_path.is_dir():
        print('Invalid output destination (must not be a directory)')
        sys.exit(1)

    if out_path.exists() and not args.overwrite:
        print('Existing file at output destination and --overwrite not passed')
        sys.exit(1)

    print()

    #%%

    print('Loading and parsing settings file...')
    try:
        settings = Settings.from_json_file(settings_path)
    except Exception:
        print('Failed to load or parse settings file')
        sys.exit(3)

    try:
        settings.check_valid()
    except Exception:
        print('Settings file invalid')
        sys.exit(4)
    print('Settings OK')

    print('Loading data...')
    try:
        data = Fmt(args.path)
    except Exception:
        print('Failed to load data')
        sys.exit(5)

    try:
        trace = data.to_trace()
    except Exception:
        print('Failed to convert loaded data to trace')
        sys.exit(101)
    print('Data loading OK')

    print('Initializing pipeline...')
    try:
        pipeline = EventExtractionPipeline(trace, settings)
    except Exception:
        print('Failed to initialize pipeline')
        sys.exit(102)
    print('Pipeline init OK')

    print('Running pipeline...')
    try:
        pipeline.run()
    except Exception:
        print('Pipeline run failed')
        sys.exit(103)
    events = pipeline.events
    if events is None:
        print('Error in event extractor')
        sys.exit(104)
    print('Pipeline run OK')

    print('Saving events...')
    attempt = 1
    base_delay = 15
    max_attempts = 3
    while True:
        try:
            events.save(out_path, overwrite=True)
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
                print('Non-OS error saving events')
                sys.exit(105)
    print('Successfully saved events')

    #%%

    print()
    sys.exit(0)
