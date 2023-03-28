# -*- coding: utf-8 -*-

from pathlib import Path
import sys

import argparse
import time

import numpy as np

from nanoporemlv2.interactiveutils.input_funcs import input_1, input_1_safe
from nanoporemlv2.featureeng.schemes import SCHEMES
from nanoporemlv2.signal.standards import STANDARDS
from nanoporemlv2.featureeng.datasetio import load_dataset, save_dataset, read_scheme, read_standard

#%%

def read_batchfile(batchfile):

    infiles = []
    with open(batchfile, 'r') as f:
        for row in f:
            stripped = row.strip()
            if stripped  == '':
                continue
            if stripped[0] == '"':
                stripped = stripped[1:]
            if stripped[-1] == ',':
                stripped = stripped[:-1]
            if stripped[-1] == '"':
                stripped = stripped[:-1]
            path = Path(stripped)
            infiles.append(path)

    return infiles

def check_exists_npz(file):
    if not file.exists():
        print('"{}" does not exist, skipping ...'.format(file))
        return False
    if file.suffix != '.npz':
        print('"{}" is not a dataset file, skipping ...'.format(file))
        return False
    return True

#%%

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--scandir", type=Path)
    parser.add_argument('--batchfile', type=Path)
    parser.add_argument("--check-scheme", choices=SCHEMES.keys())
    parser.add_argument("--check-standard", choices=STANDARDS.keys())
    parser.add_argument("infile", nargs='*', type=Path)
    parser.add_argument("outfile", type=Path)
    args = parser.parse_args()

    #%%

    print('========== combine_datasets ==========')
    print('Started at time: {}'.format(time.asctime(time.localtime())))
    print('CWD: {}'.format(Path.cwd()))
    print('Arguments: {}'.format(args))
    print()

    if args.outfile.exists() and args.outfile.is_dir():
        print('Output destination exists and is a directory, exiting ...')
        sys.exit(1)

    #%%

    print('-------- Collect input files --------')

    wanted = []
    print()

    #%%

    if args.infile:
        print('----- From args -----')
        for file in args.infile:
            if not check_exists_npz(file):
                continue
            wanted.append(file)
            print('Including "{}" for combining'.format(file))
        print()

    #%%

    if args.batchfile:
        try:
            batchfile_files = read_batchfile(args.batchfile)
        except Exception:
            print('Failed to read or parse batchfile, exiting ...')
            sys.exit(1)
        print('Successfully parsed batchfile')

        print('----- From batchfile -----')
        for file in batchfile_files:
            if not check_exists_npz(file):
                continue
            wanted.append(file)
            print('Including "{}" for combining'.format(file))
        print()

    #%%

    if args.scandir:
        if (not args.scandir.exists()) or (not args.scandir.is_dir()):
            print('Scan location does not exist or is not a directory')
        discovered_files = args.scandir.glob('**/*.dataset.npz')
        print('----- Scan -----')
        for file in discovered_files:
            if file in wanted:
                print('Found "{}". It is already included.')
            else:
                if not input_1('Found "{}". Exclude?'.format(file)):
                    wanted.append(file)
                    print('Including "{}" for combining'.format(file))
            print()
        print()

    #%%

    if len(wanted) == 0:
        print('No valid input files or none specified, exiting ...')
        sys.exit(1)

    print('----- Summary -----')
    for file in wanted:
        print(file)
    print('-----')
    if not input_1_safe('Confirm and continue?'):
        print('Exiting ...')
        sys.exit(1)
    print()

    #%%

    targets = wanted

    check_scheme = None
    if args.check_scheme:
        check_scheme = args.check_scheme

    check_standard = None
    if args.check_standard:
        check_standard = args.check_standard

    print('-------- Check meta --------')
    if check_scheme is None:
        print('Scheme for consistency check not specified, using scheme of first dataset')
    if check_standard is None:
        print('Standard for consistency check not specified, using standard of first dataset')

    check_oks = []
    check_fails = []
    print()

    for npzfile in wanted:
        print('Check "{}"'.format(npzfile))
        print('\tRead scheme ...', end=' ')
        try:
            scheme = read_scheme(npzfile)
            print('OK')
        except Exception:
            print('FAILED')
            check_fails.append(npzfile)
            continue

        print('\tScheme: ', end='')
        print(scheme, end=' ')
        if check_scheme is None:
            check_scheme = scheme
        if scheme == check_scheme:
            print('- OK')
        else:
            print('- MISMATCH')
            check_fails.append(npzfile)
            continue

        print('\tRead standard ...', end=' ')
        try:
            standard = read_standard(npzfile)
            print('OK')
        except Exception:
            print('FAILED')
            check_fails.append(npzfile)
            continue

        print('\tStandard: ', end='')
        print(standard, end=' ')
        if check_standard is None:
            check_standard = standard
        if standard == check_standard:
            print('- OK')
        else:
            print('- MISMATCH')
            check_fails.append(npzfile)
            continue

        check_oks.append(npzfile)
    print()
    print('----- Summary -----')
    print()
    print('Check OK:')
    for npzfile in check_oks:
        print('\t{}'.format(npzfile))
    print()
    print('Check FAIL:')
    for npzfile in check_fails:
        print('\t{}'.format(npzfile))
    print()
    print('------')

    if check_fails:
        if not input_1_safe('Continue with only files that passed check?'):
            print('Exiting ...')
            sys.exit(1)

    targets = check_oks
    if len(targets) == 0:
        print('No files to be combined, exiting...')
        sys.exit(0)

    #%%
    print()
    print('-------- Combine --------')
    print()
    first = True
    for npzfile in targets:
        print('Loading "{}" ...'.format(npzfile), end=' ')
        try:
            X, y = load_dataset(npzfile)
            print('OK')
            if len(X) == 0:
                print('Empty dataset ... SKIPPED')
                print()
                continue
        except Exception:
            print('FAIL')
            print('Combining ... SKIPPED')
            print()
            continue

        print('Combining ...', end=' ')
        if first:
            combined_X = X
            combined_y = y
            first = False
        else:
            combined_X = np.concatenate( (combined_X, X) )
            combined_y = np.concatenate( (combined_y, y) )
        print('DONE')
        print()
    combined_dataset = (combined_X, combined_y)
    print('--------')
    print()
    #%%

    print('-------- Save --------')
    meta = {
        'combined_from': [str(target) for target in targets]
        }
    print()
    attempt = 1
    base_delay = 15
    max_attempts = 3
    while True:
        try:
            print('Saving combined dataset to "{}", this may take a while ...'.format(args.outfile))
            save_dataset(args.outfile, *combined_dataset, check_scheme, check_standard, meta, overwrite=True)
            break
        except Exception:
            if attempt > max_attempts:
                print('Failed to save dataset and max attempts exceeded, exiting ...')
                sys.exit(16)
            else:
                delay = base_delay * attempt
                print('Failed to save dataset, reattempting after {} seconds'.format(delay))
                time.sleep(delay)
                attempt += 1

    print('Succesfully saved combined dataset')
    print()
    print('--------')

    #%%

    print()
    print('Finished at time: {}'.format(time.asctime(time.localtime())))
    print('==========')
    sys.exit(0)
