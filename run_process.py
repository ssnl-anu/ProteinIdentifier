# -*- coding: utf-8 -*-

import argparse
import time
import sys

from pathlib import Path

import subprocess
import concurrent.futures
import logging
import os

from nanoporemlv2.interactiveutils.input_funcs import input_1, input_1_safe

from nanoporemlv2.dataloaders import DATALOADERS
from nanoporemlv2.signal.standards import NONRAW_STANDARDS, input_nonraw_standard
from nanoporemlv2.featureeng.schemes import SCHEMES, input_scheme

from nanoporemlv2.featureeng.datasetio import save_dataset, load_dataset

from nanoporemlv2.mltools.datasettools import combine_datasets

#%%

def submit_tasks(executor,
                 func,
                 targets,
                 *args,
                 unpack_target=False,
                 **kwargs):
    futures = {}
    for target in targets: # This is sequential/ordered!
        if unpack_target:
            future = executor.submit(func, *target, *args, **kwargs)
        else:
            future = executor.submit(func, target, *args, **kwargs)
        futures[future] = target
    # Note that 'targets' are the "iterable args" whereas 'args' are fixed args
    # 'targets' is iterated over but 'args' is not

    # Keys are futures, values are targets that were used, everything reads
    # easier this way
    # When using with .as_completed simply use the dict since that is
    # equivalent to dict.keys() and hence same as all the futures
    # Then to get the associated target just get the value with the future as
    # key
    return futures

MAX_WORKERS_SUGGESTED = int(os.cpu_count()//2)

#%%

INTERPRETER = 'python'
INTERPRETER_ARGS = ['-O']
PYTHON = [INTERPRETER] + INTERPRETER_ARGS

def exec_run_pipeline_single(f, path, settings=None, o=None, overwrite=False):
    args = PYTHON + ['run_pipeline.py']

    args += [
        '--format', f,
        str(path)
        ]
    if settings is not None:
        args += ['--settings', str(settings)]
    if o is not None:
        args += ['--out', str(o)]
    if overwrite:
        args += ['--overwrite']

    res = subprocess.run(
        args,
        capture_output=True,
        timeout=3600
        )
    return res.returncode

def exec_run_pipeline_multi(targets, overwrite=False, max_workers=2):
    errors = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = submit_tasks(
            executor,

            exec_run_pipeline_single,
            targets,
            unpack_target=True,
            overwrite=overwrite

            )
        logging.info(f'Successfully queued {len(targets)} jobs')
        for future in concurrent.futures.as_completed(futures):
            target = futures[future]

            f, path, settings, out = target
            logging_targetrepr = f'"{path}"'

            try:
                retcode = future.result()
                if retcode != 0:
                    errors += 1
                    logging.exception(f'Job for {logging_targetrepr} failed with exit code {retcode}')
                else:
                    logging.info(f'Job for {logging_targetrepr} completed without errors')
            except Exception:
                errors += 1
                logging.exception(f'Job for {logging_targetrepr} timed out or other unexpected error')
    logging.info(f'All {len(targets)} jobs finished with errors on {errors} jobs')
    if errors:
        return 1
    else:
        return 0

def exec_events_to_signals_single(path, o=None, overwrite=False):
    args = PYTHON + ['events_to_signals.py']

    args += [str(path)]
    if o is not None:
        args += ['--out', str(o)]
    if overwrite:
        args += ['--overwrite']

    res = subprocess.run(
        args,
        capture_output=True,
        timeout=900
        )
    return res.returncode

def exec_events_to_signals_multi(targets, overwrite=False, max_workers=MAX_WORKERS_SUGGESTED):
    errors = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = submit_tasks(
            executor,

            exec_events_to_signals_single,
            targets,
            unpack_target=True,
            overwrite=overwrite

            )
        logging.info(f'Successfully queued {len(targets)} jobs')
        for future in concurrent.futures.as_completed(futures):
            target = futures[future]

            path, out = target
            logging_targetrepr = f'"{path}"'

            try:
                retcode = future.result()
                if retcode != 0:
                    errors += 1
                    logging.exception(f'Job for {logging_targetrepr} failed with exit code {retcode}')
                else:
                    logging.info(f'Job for {logging_targetrepr} completed without errors')
            except Exception:
                errors += 1
                logging.exception(f'Job for {logging_targetrepr} timed out or other unexpected error')
    logging.info(f'All {len(targets)} jobs finished with errors on {errors} jobs')
    if errors:
        return 1
    else:
        return 0

def exec_signals_to_std_signels_single(path, o=None, standard=None, overwrite=False):
    args = PYTHON + ['signals_to_std_signals.py']

    assert standard is not None
    args += [
        '--standard', standard,
        str(path)
        ]
    if o is not None:
        args += ['--out', str(o)]
    if overwrite:
        args += ['--overwrite']

    res = subprocess.run(
        args,
        capture_output=True,
        timeout=600
        )
    return res.returncode

def exec_signals_to_std_signals_multi(targets, standard, overwrite=False, max_workers=MAX_WORKERS_SUGGESTED):
    errors = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = submit_tasks(
            executor,

            exec_signals_to_std_signels_single,
            targets,
            standard,
            unpack_target=True,
            overwrite=overwrite

            )
        logging.info(f'Successfully queued {len(targets)} jobs')
        for future in concurrent.futures.as_completed(futures):
            target = futures[future]

            path, out = target
            logging_targetrepr = f'"{path}"'

            try:
                retcode = future.result()
                if retcode != 0:
                    errors += 1
                    logging.exception(f'Job for {logging_targetrepr} failed with exit code {retcode}')
                else:
                    logging.info(f'Job for {logging_targetrepr} completed without errors')
            except Exception:
                errors += 1
                logging.exception(f'Job for {logging_targetrepr} timed out or other unexpected error')
    logging.info(f'All {len(targets)} jobs finished with errors on {errors} jobs')
    if errors:
        return 1
    else:
        return 0

def exec_make_dataset_single(path, o=None, scheme=None, overwrite=False):
    args = PYTHON + ['make_dataset.py']

    assert scheme is not None
    args += [
        '--scheme', scheme,
        str(path)
        ]
    if o is not None:
        args += ['--out', str(o)]
    if overwrite:
        args += ['--overwrite']

    res = subprocess.run(
        args,
        capture_output=True,
        timeout=3600
        )
    return res.returncode

def exec_make_dataset_multi(targets, scheme, overwrite=False, max_workers=MAX_WORKERS_SUGGESTED):
    errors = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = submit_tasks(
            executor,

            exec_make_dataset_single,
            targets,
            scheme,
            unpack_target=True,
            overwrite=overwrite

            )
        logging.info(f'Successfully queued {len(targets)} jobs')
        for future in concurrent.futures.as_completed(futures):
            target = futures[future]

            path, out = target
            logging_targetrepr = f'"{path}"'

            try:
                retcode = future.result()
                if retcode != 0:
                    errors += 1
                    logging.exception(f'Job for {logging_targetrepr} failed with exit code {retcode}')
                else:
                    logging.info(f'Job for {logging_targetrepr} completed without errors')
            except Exception:
                errors += 1
                logging.exception(f'Job for {logging_targetrepr} timed out or other unexpected error')
    logging.info(f'All {len(targets)} jobs finished with errors on {errors} jobs')
    if errors:
        return 1
    else:
        return 0

#%%

STAGES = ['data', 'event', 'rawsignal', 'stdsignal', 'dataset']
STAGES_IDX = {stage: i for i, stage in enumerate(STAGES)}

#%%

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-a", "--start", choices=STAGES[:-1])
    parser.add_argument("-z", "--end", choices=STAGES[1:])
    parser.add_argument("-s", "--scan", action='store_true')
    parser.add_argument("path", type=Path)
    parser.add_argument("-f", "--format", choices=DATALOADERS.keys())
    parser.add_argument("--standard", choices=NONRAW_STANDARDS.keys())
    parser.add_argument("--scheme", choices=SCHEMES.keys())
    args = parser.parse_args()

    #%%

    if not args.path.exists():
        print(f'Path does not exist')
        sys.exit(1)

    if args.start is None:
        start = 'data'
    else:
        start = args.start
    if args.end is None:
        end = 'dataset'
    else:
        end = args.end

    start_stage_idx = STAGES_IDX[start]
    end_stage_idx = STAGES_IDX[end]
    if end_stage_idx <= start_stage_idx:
        print('End stage must be after start stage')
        sys.exit(1)

    stages = STAGES[start_stage_idx:end_stage_idx]
    print(f'Stages: {stages}')

    if 'data' in stages:
        if args.format is None:
            print('Data format must be specified')
            sys.exit(1)

    # if 'stdsignal' in stages:
    #     if args.standard is None:
    #         print('Signal standardization standard must be specified')
    #         sys.exit(1)
    ## Prompt later

    # if 'dataset' in stages:
    #     if args.scheme is None:
    #         print('Scheme for making dataset must be specified')
    #         sys.exit(1)
    ## Prompt later

    print()

    #%%

    # Only use basic logging
    handlers = [logging.StreamHandler(sys.stdout)]
    logging_fmt = \
        '%(asctime)s %(levelname)s: %(message)s'
    logging.basicConfig(
        format=logging_fmt,
        level=logging.INFO,
        handlers=handlers
        )

    #%%

    if 'data' in stages:
        Fmt = DATALOADERS[args.format]
        if args.scan:
            nonsets_ = Fmt.scan(args.path, ignore_sets=True)
            sets_ = Fmt.scan_sets(args.path)
            while True:
                nonsets = []
                sets = []
                for path in nonsets_ + sets_:
                    print(f'Found "{path}"')
                    if path in sets_:
                        print('This is a set')
                    settings_path = path.with_suffix('.json')
                    if not settings_path.exists():
                        print('Settings file not found, excluding...')
                    else:
                        print('Existing settings file found.')
                        if not input_1('Exclude?'):
                            if path in sets_:
                                sets.append(path)
                            else:
                                nonsets.append(path)
                    print()
                if input_1_safe('Confirm datas/sets?'):
                    print()
                    break
        else:
            print(f'Only "{args.path}" specified')
            if Fmt.is_set(args.path):
                sets = [args.path]
                nonsets = []
                print(f'"{args.path}" is a set.')
            else:
                sets = []
                nonsets = [args.path]
            print()


        if len(nonsets) == 0 and len(sets) == 0:
            print('No data or sets selected, exiting...')
            sys.exit(0)

        targets_ = []
        for path in nonsets:
            settings_path = path.with_suffix('.json')
            out_path = path.with_suffix('.events.npz')
            targets_.append([args.format, path, settings_path, out_path])
        for path in sets:
            members = Fmt.set_members(path)
            settings_path = path.with_suffix('.json')
            for member in members:
                out_path = member.with_suffix('.events.npz')
                targets_.append([args.format, member, settings_path, out_path])

        while True:
            targets = []
            nooverwrites = []
            for target in targets_:
                path = target[1]
                out_path = target[3]
                if out_path.exists():
                    if not input_1_safe(f'Output destination for "{path}", "{out_path}" exists. Overwrite?'):
                        nooverwrites.append(out_path)
                        continue
                targets.append(target)
            print()
            if input_1_safe('Final confirm targets?'):
                print()
                break

        print('Starting data -> event run')
        exec_run_pipeline_multi(targets, overwrite=True)
        print('Run finished, now in event stage')
        print()

    #%%

    if 'event' in stages:
        if 'data' in stages:
            prev_outs = [target[3] for target in targets]
            prev_nooverwrites = nooverwrites

            carried = prev_outs
            added = []
            if len(prev_nooverwrites) > 0:
                while True:
                    added = []
                    for path in prev_nooverwrites:
                        if input_1(f'"{path}" is not newly created previously, include in this stage anyway?'):
                            added.append(path)
                    if input_1_safe('Confirm includes?'):
                        print()
                        break
            events = carried + added

        else:
            if args.scan:
                events_ = args.path.glob('**/*.events.npz')
                while True:
                    events = []
                    for path in events_:
                        if not input_1(f'Found "{path}", exclude?'):
                            events.append(path)
                    print()
                    if input_1_safe(f'Confirm event files?'):
                        print()
                        break
                if len(events) == 0:
                    print('No event files selected, exiting...')
                    sys.exit(0)
            else:
                events = [args.path]


        targets_ = []
        for path in events:
            out_path = path.with_name(path.name[:-len('.events.npz')]+'.rawsignals.npz')
            targets_.append([path, out_path])

        while True:
            targets = []
            nooverwrites = []
            for target in targets_:
                path = target[0]
                out_path = target[1]
                if out_path.exists():
                    if not input_1_safe(f'Output destination for "{path}", "{out_path}" exists. Overwrite?'):
                        nooverwrites.append(out_path)
                        continue
                targets.append(target)
            print()
            if input_1_safe('Final confirm targets?'):
                print()
                break

        print('Starting event -> rawsignal run')
        exec_events_to_signals_multi(targets, overwrite=True)
        print('Run finished, now in rawsignal stage')
        print()

    #%%

    if 'rawsignal' in stages:
        if args.standard is None:
            while True:
                standard = input_nonraw_standard('Select standard')
                if input_1_safe('Confirm standard selection?'):
                    break
        else:
            standard = args.standard

        if 'event' in stages:
            prev_outs = [target[1] for target in targets]
            prev_nooverwrites = nooverwrites

            carried = prev_outs
            added = []
            if len(prev_nooverwrites) > 0:
                while True:
                    added = []
                    for path in prev_nooverwrites:
                        if input_1(f'"{path}" is not newly created previously, include in this stage anyway?'):
                            added.append(path)
                    if input_1_safe('Confirm includes?'):
                        print()
                        break
            rawsignals = carried + added

        else:
            if args.scan:
                rawsignals_ = args.path.glob('**/*.rawsignals.npz')
                while True:
                    rawsignals = []
                    for path in rawsignals_:
                        if not input_1(f'Found "{path}", exclude?'):
                            rawsignals.append(path)
                    print()
                    if input_1_safe(f'Confirm raw signals files?'):
                        print()
                        break
                if len(rawsignals) == 0:
                    print('No raw signals files selected, exiting...')
                    sys.exit(0)
            else:
                rawsignals = [args.path]


        targets_ = []
        for path in rawsignals:
            out_path = path.with_name(path.name[:-len('.rawsignals.npz')]+'.stdsignals.npz')
            targets_.append([path, out_path])

        while True:
            targets = []
            nooverwrites = []
            for target in targets_:
                path = target[0]
                out_path = target[1]
                if out_path.exists():
                    if not input_1_safe(f'Output destination for "{path}", "{out_path}" exists. Overwrite?'):
                        nooverwrites.append(out_path)
                        continue
                targets.append(target)
            print()
            if input_1_safe('Final confirm targets?'):
                print()
                break

        print('Starting rawsignals -> stdsignal run')
        exec_signals_to_std_signals_multi(targets, standard, overwrite=True)
        print('Run finished, now in rawsignal stage')
        print()

    #%%

    if 'stdsignal' in stages:
        if args.scheme is None:
            while True:
                scheme = input_scheme('Select scheme')
                if input_1_safe('Confirm scheme selection?'):
                    break
        else:
            scheme = args.scheme

        if 'rawsignal' in stages:
            prev_outs = [target[1] for target in targets]
            prev_nooverwrites = nooverwrites

            carried = prev_outs
            added = []
            if len(prev_nooverwrites) > 0:
                while True:
                    added = []
                    for path in prev_nooverwrites:
                        if input_1(f'"{path}" is not newly created previously, include in this stage anyway?'):
                            added.append(path)
                    if input_1_safe('Confirm includes?'):
                        print()
                        break
            stdsignals = carried + added

        else:
            if args.scan:
                stdsignals_ = args.path.glob('**/*.stdsignals.npz')
                while True:
                    stdsignals = []
                    for path in stdsignals_:
                        if not input_1(f'Found "{path}", exclude?'):
                            stdsignals.append(path)
                    print()
                    if input_1_safe(f'Confirm standardized signals files?'):
                        print()
                        break
                if len(stdsignals) == 0:
                    print('No standardized signals files selected, exiting...')
                    sys.exit(0)
            else:
                stdsignals = [args.path]


        targets_ = []
        for path in stdsignals:
            out_path = path.with_name(path.name[:-len('.stdsignals.npz')]+'.dataset.npz')
            targets_.append([path, out_path])

        while True:
            targets = []
            nooverwrites = []
            for target in targets_:
                path = target[0]
                out_path = target[1]
                if out_path.exists():
                    if not input_1_safe(f'Output destination for "{path}", "{out_path}" exists. Overwrite?'):
                        nooverwrites.append(out_path)
                        continue
                targets.append(target)
            print()
            if input_1_safe('Final confirm targets?'):
                print()
                break

        print('Starting stdsignals -> dataset run')
        exec_make_dataset_multi(targets, scheme, overwrite=True)
        print('Run finished, now in dataset stage')
        print()

    #%%

        if 'data' in stages:
            print('Making combined dataset for sets')
            for path in sets:
                abort = False
                members = Fmt.set_members(path)
                out_path = path.with_suffix('.dataset.npz')
                if out_path.exists():
                    if not input_1_safe(f'Combined file for set "{path}", "{out_path}" exists, overwrite?'):
                        continue
                datasets = []
                for member in members:
                    dataset_path = member.with_suffix('.dataset.npz')
                    try:
                        dataset = load_dataset(dataset_path)
                    except:
                        print(f'Failed to load dataset of member "{member}", aborting combine for this set...')
                        abort = True
                        break
                    datasets.append(dataset)
                if abort:
                    continue
                combined_dataset = combine_datasets(*datasets)
                meta = {
                    'combined_from': [str(member) for member in members]
                    }
                save_dataset(out_path, *combined_dataset, scheme, standard, meta, overwrite=True)


    #%%

    print('Program completed')
    sys.exit(0)
