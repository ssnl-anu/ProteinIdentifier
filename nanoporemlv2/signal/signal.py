# -*- coding: utf-8 -*-

from warnings import warn

from collections import UserList

import copy

from pathlib import Path
from zipfile import ZipFile
import json

import numpy as np

from ..utils.casting import cast_1d_nonempty_numeric_array
from ..utils import npztools

from ..dataloaders.common import Trace, Info

from .standards import STANDARDS, check_standard

#%%
# This class needs to be relatively high performance
# Avoid copying unless absolutely necessary
# Ok to do validation though
class Signal:
    def __init__(self, values, trace_info=None):
        self.values = values
        if trace_info is None:
            trace_info = Info()
        self.trace_info = trace_info
        self._standard = None

    @property
    def standard(self):
        return self._standard

    @property
    def values(self):
        return self._values

    @values.setter
    def values(self, array_like):
        self._values = cast_1d_nonempty_numeric_array(array_like)

    @property
    def trace_info(self):
        return self._trace_info # Reference to original trace info

    @trace_info.setter
    def trace_info(self, obj):
        if obj is not None:
            if not isinstance(obj, Info):
                raise ValueError(f'Not an Info object: {obj}')
        self._trace_info = obj
        self._standardized_values = None

    @property
    def standard(self):
        return self._standard

    def __str__(self):
        return str(self.values)

    def __repr__(self):
        return f'<Signal {str(self.values)}>'

    def __len__(self):
        return len(self.values)

    def copy(self):
        new_signal = copy.copy(self)
        new_signal._values = self._values.copy()
        return new_signal

    @staticmethod
    def _standardize(signal, standard):
        if signal.standard != 'raw':
            raise ValueError(f'Signal is already standardized: {signal.standard}')
        Signal._standardize_nocheckraw(signal, standard)

    @staticmethod
    def _standardize_nocheckraw(signal, standard):
        STANDARDS[standard](signal)
        signal._standard = standard

    def standardize(self, standard):
        check_standard(standard)
        self.__class__._standardize(self, standard)

    def standardized(self, standard):
        check_standard(standard)
        std_signal = self.copy()
        std_signal._standardize(standard)
        return std_signal

    def has_nan(self):
        return np.any(np.isnan(self.values))

    def has_neg(self):
        return np.any(self.values < 0)

#%%

class Signals(UserList):
    def __init__(self, signals):
        for signal in signals:
            if not isinstance(signal, Signal):
                raise ValueError(f'Not a Signal object: {signal}')
        self.data = signals
        self._loaded_from = None
        self._loaded_meta = None
        self._loaded_trace_info = None
        self._loaded_standard = None
        self._extracted_from = None
        self._set_standard = None

    @property
    def signals(self):
        return self.data

    @property
    def loaded_from(self):
        return self._loaded_from

    @property
    def loaded_meta(self):
        return self._loaded_meta

    @property
    def extracted_from(self):
        return self._extracted_from

    @property
    def trace_info(self):
        if self.loaded_from is not None:
            return self._loaded_trace_info
        elif self.extracted_from is not None:
            return self.extracted_from.trace_info
        else:
            return self.signals[0].trace_info

    @property
    def standard(self):
        if self._set_standard is not None: # Standardized after loading
            return self._set_standard
        if self._loaded_from is not None: # Loaded signals
            return self._loaded_standard
        if self._extracted_from is not None: # Just extracted signals
            return 'raw'
        else:
            return self.signals[0].standard

    def check_consistent(self):
        ref_trace_info_dic = self.trace_info.to_dict()
        ref_standard = self.standard
        for signal in self.signals:
            if signal.trace_info.to_dict() != ref_trace_info_dic:
                raise ValueError(f'Inconsistent signal: {signal}')
            if signal.standard != ref_standard:
                raise ValueError(f'Inconsistent standard: {signal}, {signal.standard}')

    def copy(self):
        new_signals = self.copy()
        for i in range(len(new_signals)):
            new_signals[i] = new_signals[i].copy()
        return new_signals

    def _standardize(self, standard):
        for signal in self.signals:
            Signal._standardize_nocheckraw(signal, standard)
        self._set_standard = standard

    def _pre_standardize_checks(self):
        if self.standard != 'raw':
            raise ValueError(f'Cannot standardize non-raw signals')
        self.check_consistent()

    def standardize(self, standard):
        check_standard(standard)
        self._pre_standardize_checks()
        self._standardize(standard)

    def standardized(self, standard):
        check_standard(standard)
        self._pre_standardize_checks()
        standardized_signals = self.copy()
        standardized_signals._standarize(standard)
        return standardized_signals

    def remove_filtered(self, *filters):
        good = []
        bad_count = 0
        for signal in self.signals:
            for filt in filters:
                if filt(signal) == True:
                    bad_count += 1
                    continue
            good.append(signal)
        self.data = good
        return bad_count

    def remove_has_nan_signals(self):
        return self.remove_filtered(lambda signal: signal.has_nan())

    def remove_has_neg_signals(self):
        return self.remove_filtered(lambda signal: signal.has_neg())

    def meta_dict(self):
        '''
        On real first save:

            If events source is loaded events file:
                Want source to say that event file
                Want to include copy of event file's meta

            If instead event source is not loaded from an events file:
                Want souce to say just "events"
                Want to include would-be event file's meta

        On second save:
            Want source to now say the original signals file
            Want to keep copy of original signals file's source, since that is events source, and also keep copy of events meta
                This is just all of original signals file's meta

        On subsequent saves:
            Want source to say the previous signals file
            Want to carry the meta of original signals file
                DO not want to make a copy of previous since the source of that is not events source
        '''
        dic = {}

        assert not ( (self._loaded_from is not None) and (self._extracted_from is not None) )

        if self._loaded_from is not None: # Not first save
            dic['source'] = str(self._loaded_from.absolute())
            loaded_meta = self._loaded_meta
            if 'original_meta' in loaded_meta: # Not second save
                dic['original_meta'] = loaded_meta['original_meta']
            else: # Second save
                dic['original_meta'] = loaded_meta

        else: # First save
            dic['source'] = None
            if self._extracted_from is not None:

                if self._extracted_from.loaded_from is not None: # Loaded events file
                    dic['source'] = str(self._extracted_from.loaded_from.absolute())
                    dic['source_meta'] = self._extracted_from.loaded_meta
                else: # Events not loaded from file
                    dic['source'] = 'events'
                    dic['source_meta'] = self._extracted_from.meta_dict()

        return dic

    @staticmethod
    def save_(path, signals, overwrite=False):
        path = Path(path)

        standard = signals.standard
        assert isinstance(standard, str)

        if standard is None:
            sec_suffix = '.signals'
        elif standard == 'raw':
            sec_suffix = '.rawsignals'
        else:
            sec_suffix = '.stdsignals'

        # WHERE SUFFIX CONFLICTS WITH EMBEDDED STANDARD.TXT, STANDARD.TXT IS DEFINITIVE

        if path.suffixes[-2:] != [sec_suffix, '.npz']:
            path = path.with_suffix(path.suffix + sec_suffix + '.npz')

        meta = signals.meta_dict()

        signals.check_consistent()

        mode = 'xb'
        if overwrite:
            mode = 'wb'

        arrs = [signal.values for signal in signals.signals]
        with open(path, mode) as f:
            np.savez_compressed(f, *arrs)

        with ZipFile(path, 'a') as zf:
            zf.writestr(
                'standard.txt',
                signals.standard
                )
            zf.writestr(
                'trace_info.json',
                signals.trace_info.to_json()
                )
            zf.writestr(
                'meta.json',
                json.dumps(meta, indent=2)
                )

    def save(self, path, overwrite=False):
        self.__class__.save_(path, self, overwrite=overwrite)

    @classmethod
    def load(cls, path):
        path = Path(path)

        npzf = np.load(path)

        meta = json.loads(npzf['meta.json'])

        trace_info = Info.from_json(npzf['trace_info.json'])
        try:
            trace_info.check_valid()
        except Exception:
            warn('Trace info not (fully) valid')

        standard = npztools.readstr(npzf, 'standard.txt')
        if standard not in STANDARDS.keys():
            warn(f'Unrecognized standard: {standard}')

        arr_names = npztools.get_arr_filenames(npzf)
        signals = []
        for arr_name in arr_names:
            signal = Signal(npzf[arr_name], trace_info=trace_info)
            signal._standard = standard
            signals.append(signal)

        signals = cls(signals)
        signals._loaded_from = path
        signals._loaded_meta = meta
        signals._loaded_standard = standard
        signals._loaded_trace_info = trace_info

        return signals

    @staticmethod
    def scan(path, recursive=True):
        scan_dir = Path(path)

        if recursive:
            glob_pattern = '**/*.signals.npz'
        else:
            glob_pattern = '*.signals.npz'

        return list(scan_dir.glob(glob_pattern))
