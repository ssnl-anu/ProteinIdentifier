# -*- coding: utf-8 -*-

from pathlib import Path

from .common import Trace, Info

import pyabf

class ABF(pyabf.ABF):
    name = 'abf'
    '''
    Interface for Axon Binary File Format (ABF) data

    There are two major versions of this format, 1.x and 2.0
    Our data should be version 2.0

    Official documentation for both is at
    https://www.moleculardevices.com/sites/default/files/en/assets/user-guide/dd/cns/axon-binary-file-format-v2-0-9.pdf

    Version 1.x is well documented by official documentation
    Version 2.0 is however proprietary and not well documented by official documentation (intentionally)

    ABF 2.0 has however been reverse engineered by people
    See https://swharden.com/pyabf/abf2-file-format/

    A python library (pyABF) for reading files is also available by the same developer
    This supports both 1.x and 2.0 versions

    This library will be used

    This class is just a wrapper that additionally checks that the file suffix is indeed .abf
    Not strictly necessary but I just wanted somewhere to put the above info in so...
    '''

    def __init__(self, abf_file):
        if Path(abf_file).suffix != '.abf':
            raise ValueError('Not an ABF file')

        super().__init__(abf_file)

    assert 'to_trace' not in dir(pyabf.ABF)

    def to_trace(self):
        if self.adcUnits[0] != 'nA':
            raise NotImplementedError('ABF sweep units is not nA')
        return Trace(
            self.sweepY,
            time=self.sweepX,
            info=Info(
                sampling_rate=self.dataRate
                ),
            raw=self
            )

    @property
    def path(self):
        return Path(self.abfFilePath)

    @staticmethod
    def scan(path, recursive=True, ignore_sets=True):
        scan_dir = Path(path)

        if recursive:
            glob_pattern = '**/*.abf'
        else:
            glob_pattern = '*.abf'

        if ignore_sets:
            ret = []
            for path in scan_dir.glob(glob_pattern):
                if not (path.parent/'this_is_a_set.txt').exists():
                    ret.append(path)
            return ret
        else:
            return list(scan_dir.glob(glob_pattern))

    @staticmethod
    def scan_sets(path, max_depth=4):
        if type(max_depth) != int or max_depth < 0:
            raise ValueError('Invalid max recurse depth')

        scan_dir = Path(path)

        datadirs = []
        subdirs = []
        for child in scan_dir.iterdir():
            if ABF.is_set(child):
                datadirs.append(child)
            elif child.is_dir():
                subdirs.append(child)
            # else:
            #    continue
        if max_depth > 0:
            for subdir in subdirs:
                datadirs.extend( ABF.scan_sets(subdir, max_depth=max_depth-1) )
        return datadirs

    @staticmethod
    def is_set(path):
        path = Path(path)
        if not path.is_dir():
            return False
        if any(path.glob('*.abf')) and (path/'this_is_a_set.txt').exists():
            return True
        else:
            return False

    @staticmethod
    def set_members(path):
        return list(path.glob('*.abf'))
