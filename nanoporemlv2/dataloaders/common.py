# -*- coding: utf-8 -*-

from warnings import warn

from pprint import pp

import copy

import numpy as np

from ..utils.paramcontainer import ParamContainer
from ..utils.casting import cast_1d_nonempty_numeric_array
from ..utils.validators import check_bool, check_eq_shape, check_numeric, check_positive_numeric, check_positive_int, check_nonnegative_int

from ..interactiveutils.input_funcs import input_1_safe, input_float, input_1_default, input_str_default, input_1
from ..interactiveutils.scrollablefig import ScrollableFig

from . import LABELS, input_label

from .poreinfo import PORE_INFO_DICT, reload_pore_info

#%%

class Trace:
    def __init__(self, current, time=None, info=None, raw=None):
        self.current = current
        self.info = info
        self.raw = raw
        if time is not None:
            self.time = time

    @property
    def current(self):
        return self._current

    @current.setter
    def current(self, array_like):
        self._current = cast_1d_nonempty_numeric_array(array_like)

    @property
    def info(self):
        return self._info

    @info.setter
    def info(self, obj):
        obj = Info(obj)
        self._info = obj

    def __len__(self):
        return len(self.current)

    @property
    def time(self):
        if self._time is None:
            # Integer range then scale by period to minimize floating point precision issues
            # np.arange instead of range as it is more performant
            time_ = np.arange(0, len(self), 1) * self.info.sample_period
            self._time = time_
        return self._time

    @time.setter
    def time(self, array_like):
        time_ = cast_1d_nonempty_numeric_array(array_like)
        check_eq_shape(self.current, time_)
        self._time = time_

    def copy(self):
        new_trace = copy.copy(self)
        new_trace.current = self.current.copy()
        return new_trace

    def apply_mask(self, mask):
        self.current[mask] = np.nan

    def masked(self, mask):
        new_trace = self.copy()
        new_trace.apply_mask(mask)
        return new_trace

    def __getitem__(self, key):
        if type(key) != slice:
            raise TypeError('Not subscriptable')
        new_trace = self.copy()
        new_trace.current = new_trace.current[key]
        new_trace.time = new_trace.time[key]
        return new_trace

    def interactive_fill_info(self):
        if self.raw is not None:
            print(f'Trace was created from: "{self.raw.path.absolute()}"')

        if self.info.sampling_rate is None or \
        input_1(f'Overwrite sampling rate loaded from data ({self.info.sampling_rate}Hz)?'):
            while True:
                sampling_rate = input_float(
                    'Enter sampling rate in Hz',
                    pos_only=True,
                    default=self.info.sampling_rate
                    )
                if input_1_safe(f'Confirm sampling rate of {sampling_rate}Hz?'):
                    self.info.sampling_rate = sampling_rate
                    break


        while True:
            label = input_label('Enter label', default=self.info.label)
            if input_1_safe(f'Confirm label is "{label}"?'):
                self.info.label = label
                break

        while True:
            signed_voltage = input_float(
                'Enter SIGNED voltage in volts',
                pos_only=False,
                default=self.info.signed_voltage
                )
            if input_1_safe(f'Confirm voltage of {signed_voltage:+f}V?'):
                self.info.signed_voltage = signed_voltage
                break

        while True:
            pore_id = input_str_default('Enter pore id', default=self.info.pore_id)
            if input_1_safe(f'Confirm pore id is "{pore_id}"?'):
                bad = True
                try:
                    self.info.pore_id = pore_id
                    bad = False
                except KeyError:
                    print('Pore id invalid or not in database. Please add pore to database if new pore.')

                if not bad:
                    print('Retrieved pore info:')
                    pp(self.info.pore_info)
                    if input_1_safe('Confirm pore info?'):
                        break

                if input_1_safe('Reload pore info from database before prompt pore id again?'):
                    reload_pore_info()

        sfig = ScrollableFig()
        sfig.plot(self.time, self.current)

        while True:
            peaks_not_dips = input_1_default(
                'Are events peaks rather than dips?',
                default=self.info.peaks_not_dips
                )
            if input_1_safe('Confirm events are {}?'.format('peaks' if peaks_not_dips else 'dips')):
                self.info.peaks_not_dips = peaks_not_dips
                break

        while True:
            max_event_width_seconds = input_float(
                'Enter (hard) maximum event width',
                pos_only=True,
                default=self.info.max_event_width_seconds
                )

            if input_1_safe(f'Confirm max event width of {max_event_width_seconds}s?'):
                self.info.max_event_width_seconds = max_event_width_seconds
                break

        while True:
            min_event_width_seconds = input_float(
                'Enter (hard) minimum event width',
                pos_only=True,
                default=self.info.min_event_width_seconds
                )
            if input_1_safe(f'Confirm min event width of {min_event_width_seconds}?'):
                self.info.min_event_width_seconds = min_event_width_seconds
                break

        sfig.close()
        pp(self.info.to_dict())

        return self.info

#%%

class Info(ParamContainer):

    def _init(
            self,
            sampling_rate=None,
            label=None,
            signed_voltage=None,
            pore_id=None,
            peaks_not_dips=None,
            max_event_width_seconds=None,
            min_event_width_seconds=None
            ):
        self.sampling_rate = sampling_rate
        self.label = label
        self.signed_voltage = signed_voltage
        self.pore_id = pore_id
        self.peaks_not_dips = peaks_not_dips
        self.max_event_width_seconds = max_event_width_seconds
        self.min_event_width_seconds = min_event_width_seconds

    @property
    def sampling_period(self):
        return self._sampling_period

    @sampling_period.setter
    def sampling_period(self, value):
        check_numeric(value)
        value = float(value)
        if value > 0.010:
            warn(f'Sampling period longer than 0.010s (10ms): {value}')
        self._sampling_period = value
        self._sampling_rate = int(1/value)

    @property
    def sampling_rate(self):
        return self._sampling_rate

    @sampling_rate.setter
    def sampling_rate(self, value):
        if value is not None:
            check_numeric(value)
            value = float(value)
            if value < 10_000:
                warn(f'Sampling rate lower than 10,000Hz (10kHz): {value}')
        self._sampling_rate = value
        if value is not None:
            self._sampling_period = float(1/value)
        else:
            self._sampling_period = None

    def to_samples(self, seconds):
        check_numeric(seconds)
        seconds = float(seconds)
        return int(seconds/self.sampling_period)

    def to_seconds(self, samples):
        check_numeric(samples)
        samples = int(samples)
        return float(samples * self.sampling_period)

    @property
    def label(self):
        return self._label

    @label.setter
    def label(self, value):
        if (value is not None) and (value not in LABELS):
            raise ValueError(f'Not a valid label: {value}')
        self._label = value

    @property
    def signed_voltage(self):
        return self._signed_voltage

    @signed_voltage.setter
    def signed_voltage(self, value):
        if value is not None:
            check_numeric(value)
            value = float(value)
            if abs(value) < 1e-6:
                warn(f'Signed voltage less than 1e-6V (1uV): {value}')
        self._signed_voltage = value

    @property
    def pore_id(self):
        return self._pore_id

    @pore_id.setter
    def pore_id(self, value):
        if value is not None and value not in PORE_INFO_DICT:
            raise KeyError(f'Invalid pore id or pore not in database: {value}')
        self._pore_id = value

    @property
    def pore_info(self):
        return PORE_INFO_DICT[self.pore_id]

    @property
    def peaks_not_dips(self):
        return self._peaks_not_dips

    @peaks_not_dips.setter
    def peaks_not_dips(self, value):
        if value is not None:
            check_bool(value)
        self._peaks_not_dips = value

    @property
    def max_event_width_seconds(self):
        return self._max_event_width_seconds

    @max_event_width_seconds.setter
    def max_event_width_seconds(self, value):
        if value is not None:
            check_positive_numeric(value)
            if value > 0.050:
                warn(f'Max event width longer than 0.050s (50ms): {value}')
            if value < 0.000_250:
                warn(f'Max event width shorter than 0.000250s (250us): {value}')
            value = float(value)
        self._max_event_width_seconds = value

    @property
    def max_event_width_samples(self):
        return self.to_samples(self.max_event_width_seconds)

    @max_event_width_samples.setter
    def max_event_width_samples(self, value):
        check_positive_int(value)
        self._max_event_width_seconds = self.to_seconds(value)

    @property
    def min_event_width_seconds(self):
        return self._min_event_width_seconds

    @min_event_width_seconds.setter
    def min_event_width_seconds(self, value):
        if value is not None:
            check_positive_numeric(value)
            if value > 0.000_025:
                warn(f'Min event width longer than 0.000025s (25us)')
            value = float(value)
        self._min_event_width_seconds = value

    @property
    def min_event_width_samples(self):
        return self.to_samples(self.min_event_width_seconds)

    @min_event_width_samples.setter
    def min_event_width_samples(self, value):
        check_nonnegative_int(value)
        self._min_event_width_seconds = self.to_seconds(value)

    def to_dict(self):
        dic = {
            'sampling_rate': self.sampling_rate,
            'label': self.label,
            'signed_voltage': self.signed_voltage,
            'pore_id': self.pore_id,
            'peaks_not_dips': self.peaks_not_dips,
            'max_event_width_seconds': self.max_event_width_seconds,
            'min_event_width_seconds': self.min_event_width_seconds
            }
        return dic

    def check_valid(self):
        if self.sampling_rate is None:
            raise ValueError('Sampling rate not specified')
        if self.label is None:
            raise ValueError('Label not specified')
        if self.signed_voltage is None:
            raise ValueError('Signed voltage not specified')
        if self.pore_id is None:
            raise ValueError('Pore ID not specified')
        if self.max_event_width_seconds is None:
            raise ValueError('Max event width (seconds) not specified')
        if self.min_event_width_seconds is None:
            raise ValueError('Min event width (seconds) not specified')
        min_max_diff_samples = self.max_event_width_samples - self.min_event_width_samples
        if min_max_diff_samples <= 0:
            raise ValueError(f'Max event width smaller than or equal to min event width in terms of samples: {self.max_event_width_samples}, {self.min_event_width_samples}')
        if min_max_diff_samples < 10:
            warn(f'Max event width is only larger than min event width by less than 10 samples: {min_max_diff_samples}')

#%%

class DataLoader:

    def to_trace(self):
        raise NotImplementedError

    @staticmethod
    def scan(path, ignore_sets=True, **kwargs):
        raise NotImplementedError

    @staticmethod
    def scan_sets(path, max_depth=4, **kwargs):
        raise NotImplementedError

    @staticmethod
    def is_set(path):
        raise NotImplementedError

    @staticmethod
    def set_members(path):
        raise NotImplementedError

    @property
    def path(self):
        return NotImplementedError
