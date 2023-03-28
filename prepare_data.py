# -*- coding: utf-8 -*-

import argparse
import time
import sys

from pathlib import Path

from nanoporemlv2.interactiveutils.input_funcs import input_1, input_1_safe

from nanoporemlv2.dataloaders import DATALOADERS

from nanoporemlv2.eventextraction.pipeline import EventExtractionPipeline, Settings

#%%

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--format", choices=DATALOADERS.keys(), required=True)
    parser.add_argument("-s", "--scan", action='store_true')
    parser.add_argument("path", type=Path)
    args = parser.parse_args()

    #%%

    print('========== prepare_data.py ==========')
    print(f'Started at time: {time.asctime(time.localtime())}')
    print(f'CWD: {Path.cwd()}')
    print(f'Arguments: {args}')
    print()

    #%%

    Fmt = DATALOADERS[args.format]

    #%%

    if args.scan:
        nonsets_ = Fmt.scan(args.path, ignore_sets=True)
        sets_ = Fmt.scan_sets(args.path)
        while True:
            nonsets = []
            sets = []
            for path in nonsets_ + sets_:
                prompt = f'Found "{path}", exclude?'
                if path in sets_:
                    prompt += ' This is a set.'
                settings_path = path.with_suffix('.json')
                if settings_path.exists():
                    prompt += ' Existing settings file found.'
                if not input_1(prompt):
                    if path in sets_:
                        sets.append(path)
                    else:
                        nonsets.append(path)
            if input_1_safe('Confirm targets?'):
                break
    else:
        if not args.path.exists():
            print(f'Data not found')
            sys.exit(1)
        if Fmt.is_set(args.path):
            sets = [args.path]
            nonsets = []
        else:
            sets = []
            nonsets = [args.path]

    if len(nonsets) == 0 and len(sets) == 0:
        print('No targets selected, exiting...')
        sys.exit(0)

    #%%

    for path in nonsets + sets:
        if path in nonsets:
            data = Fmt(path)
        else:
            first_member = Fmt.set_members(path)[0]
            data = Fmt(first_member)

        trace = data.to_trace()
        settings = None
        settings_path = path.with_suffix('.json')
        if settings_path.exists():
            try:
                settings = Settings.from_json_file(settings_path)
            except Exception:
                settings = None
        settings = EventExtractionPipeline.interactive_gen_settings(trace, settings)

        #%%

        write_settings = True
        did_not_save = True

        if settings_path.exists():
            write_settings = False
            write_settings = input_1_safe(
                f'Settings file destination "{settings_path.absolute()}" exists, overwrite?'
                )

        if write_settings:
            while True:
                print(f'Saving settings to "{settings_path}"... ', end='')
                try:
                    settings.to_json_file(settings_path, overwrite=True)
                    print('SUCCESS')
                    did_not_save = False
                    break
                except (BlockingIOError, PermissionError):
                    print('FAILED')
                    if not input_1_safe('Retry save settings?'):
                        break

        if did_not_save:
            print('Printing settings file contents for manual file creation...')
            print(f'##### "{settings_path.absolute()}" #####')
            print(settings.to_json())
            print('###########')

        print()

    #%%

    print()
    sys.exit(0)
