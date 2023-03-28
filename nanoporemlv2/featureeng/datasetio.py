# -*- coding: utf-8 -*-
from warnings import warn

from pathlib import Path
from zipfile import ZipFile
import json

from pprint import pp

import numpy as np

from ..utils import npztools

from ..signal.standards import STANDARDS
from .schemes import SCHEMES, check_scheme

def make_dataset(signals, scheme):
    check_scheme(scheme)
    signals.check_consistent()

    scheme_func = SCHEMES[scheme]

    any_fails = False
    vectors = []
    for signal in signals.signals:
        try:
            vector = scheme_func(signal)
        except Exception: # Use this to reject signals from scheme POV
            any_fails = True
            continue
        vectors.append(vector)

    X = np.array(vectors)
    y = np.full(
        (len(vectors), ),
        signals.trace_info.label
        )

    return X, y

def save_dataset(path, X, y, scheme=None, standard=None, meta=None, overwrite=False):
    '''
    As dataset may be manipulated heavily in ML scripts,
    There will be no strict requirements for any metadata

    Recommended for user to at minimum carry the scheme and standard
    Keeping track of meta however may be too taxing, and can be said to be optional.

    Dependent code should NOT rely on meta being complete or having any certain structure
    Saved meta also need not carry full history, but should aim to

    Users may at their own risk rely on the presence of scheme and standard
    User code should of course save scheme and standard when saving if relying on these fields

    On first creation, use make_and_save_dataset
    This will fill scheme and standard
    meta will be generated from source signals.
    '''
    path = Path(path)

    if path.suffixes[-2:] != ['.dataset', '.npz']:
        path = path.with_suffix(path.suffix + '.dataset.npz')

    assert len(X) == len(y)

    if scheme is None:
        scheme = ''
    else:
        if not isinstance(scheme, str):
            raise ValueError(f'Not a str: {scheme}')
        if scheme not in SCHEMES:
            warn(f'Unrecognized scheme: {scheme}')

    if standard is None:
        standard = ''
    else:
        if not isinstance(scheme, str):
            raise ValueError(f'Not a str: {standard}')
        if standard not in STANDARDS:
            warn(f'Unrecognized scheme: {standard}')

    if meta is None:
        meta = {}
    if not isinstance(meta, dict):
        raise ValueError(f'Not a dict: {meta}')

    mode = 'xb'
    if overwrite:
        mode = 'wb'
    with open(path, mode) as npzf:
        np.savez_compressed(npzf, X=X, y=y)

    with ZipFile(path, 'a') as zf:
        zf.writestr(
            'scheme.txt',
            scheme
            )
        zf.writestr(
            'standard.txt',
            standard
            )
        zf.writestr(
            'meta.json',
            json.dumps(meta, indent=2)
            )

def gen_dataset_meta(signals):
    meta = {}
    if signals.loaded_from is not None:
        meta['source'] = str(signals.loaded_from)
        meta['source_meta'] = signals.loaded_meta
    else:
        meta['source'] = 'signals'
        meta['source_meta'] = signals.meta_dict()
    return meta

def make_and_save_dataset(signals, scheme, path, overwrite=False):
    dataset = make_dataset(signals, scheme)
    standard = signals.standard
    meta = gen_dataset_meta(signals)
    save_dataset(path, *dataset, scheme=scheme, standard=standard, meta=meta, overwrite=overwrite)

def load_dataset(path, return_dataset_only=True):
    path = Path(path)

    npzf = np.load(path)

    X = npzf['X']
    y = npzf['y']

    if return_dataset_only:
        return X, y
    else:
        scheme = npztools.readstr(npzf, 'scheme.txt')
        standard = npztools.readstr(npzf, 'standard.txt')
        meta = json.loads(npzf['meta.json'])
        return X, y, scheme, standard, meta

def read_scheme(path):
    path = Path(path)
    npzf = np.load(path)
    scheme = npztools.readstr(npzf, 'scheme.txt')
    return scheme

def read_standard(path):
    path = Path(path)
    npzf = np.load(path)
    standard = npztools.readstr(npzf, 'standard.txt')
    return standard

def scan_for_datasets(path, recursive=True):
    scan_dir = Path(path)

    if recursive:
        glob_pattern = '**/*.dataset.npz'
    else:
        glob_pattern = '*.dataset.npz'

    return list(scan_dir.glob(glob_pattern))

def recursive_find_key(dic, key):
    for k, v in dic.items():
        if k == key:
            return v
        elif isinstance(v, dict):
            try:
                return recursive_find_key(v,key)
            except KeyError:
                pass
    raise KeyError(f'Key not found: {key}')

def get_meta_value(meta, key):
    '''Alias for recursive_find_key'''
    return recursive_find_key(meta, key)

def load_separated_by_meta(meta_key, *paths):
    if meta_key not in ['signed_voltage', 'pore_id']:
        warn(f'Not a recommended meta key to use for separation: {meta_key}')

    separated = {}
    separated_paths = {}
    for path in paths:
        X, y, _, _, meta = load_dataset(path, return_dataset_only=False)
        dataset = X, y
        try:
            group = get_meta_value(meta, meta_key)
        except KeyError:
            warn(f'Meta key "{meta_key}" not found in the meta of "{path}", excluding this dataset')
            continue
        if group not in separated:
            separated[group] = [dataset]
            separated_paths[group] = [path.as_posix()]
        else:
            separated[group].append(dataset)
            separated_paths[group].append(path.as_posix())

    print('Separated - group paths:')
    pp(separated_paths, indent=2)

    counts = {}
    for k, v in separated_paths.items():
        counts[k] = len(v)
    print('Separated - group counts:', counts)

    return separated
