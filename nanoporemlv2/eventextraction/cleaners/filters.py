# -*- coding: utf-8 -*-

from warnings import warn

import numpy as np
import scipy.signal as sig

from ...utils.validators import check_positive_int, check_nonnegative, check_bool
from ...utils.paramcontainer import ParamContainer

from ...interactiveutils.input_funcs import input_1_safe, make_input_opt, input_float, input_int_strict

from .common import Cleaner

#%%

def combine_sos(*soses):
    return np.concatenate( soses )

#%%

# Note: filtfilt is used since it results in zero phase response
# We can use filtfilt since all our data are "offline" i.e. we are not running live (real-time)
# filtfilt delays the entire signal by abit, we can accept this since we do not care about absolute time

# All filters should be first designed with sos output where possible
# So as to minimize unwanted distortions from numerical instability

#%%

PRESETS = {
    'Elements200kHz_Custom35kLPF': combine_sos(
        sig.butter(8, fs=200_000, Wn=35000, btype='lowpass', output='sos'), # Basic 35kHz fc LPF
        sig.butter(8, fs=200_000, Wn=(35000, 60000), btype='bandstop', output='sos') # Additional bandstop to rid strong 39kHz noise band + enhance LPF effect
        )
    }

for key, sos in PRESETS.items():
    assert isinstance(key, str)
    assert isinstance(sos, np.ndarray)
    assert sos.shape[1] == 6

input_preset = make_input_opt(PRESETS.keys())

#%%

class PresetFilter(Cleaner):
    name = 'presetfilter'

    class Params(ParamContainer):
        def _init(
                self,
                preset=None,
                # filtfilt=True
                ):
            self.preset = preset

        @property
        def preset(self):
            return self._preset

        @preset.setter
        def preset(self, value):
            if value is not None:
                if value not in PRESETS:
                    raise ValueError('Invalid present')
            self._preset = value

        # @property
        # def filtfilt(self):
        #     return self._filtfilt

        # @filtfilt.setter
        # def filtfilt(self, value):
        #     check_bool(value)
        #     self._filtfilt = value

        def check_valid(self):
            pass

        def to_dict(self):
            dic = {
                'preset': self.preset
                }
            return dic

    @staticmethod
    def _run(trace, params):
        sos = PRESETS[params.preset]
        filtered = sig.sosfiltfilt(sos, trace.current)
        # filtered = sig.sosfilt(sos, trace.current)
        new_trace = trace.copy()
        new_trace.current = filtered
        return new_trace

    @classmethod
    def _interactive_gen_params(cls, trace, params):
        while True:
            preset = input_preset('Choose preset', default=params.preset)
            if input_1_safe('Confirm preset?'):
                params.preset = preset
                break
        return params

#%%

class LowPassFilter(Cleaner):
    name = 'lowpassfilter'

    class Params(ParamContainer):
        def _init(
                self,
                fc=None,
                N=8
                ):
            self.fc = fc
            self.N = 8

        @property
        def fc(self):
            return self._fc

        @fc.setter
        def fc(self, value):
            if value is not None:
                check_nonnegative(value)
                if value <= 1:
                    warn('Small critical frequency (fc should be in Hz not normalized units): {value}')
            self._fc = value

        @property
        def N(self):
            return self._N

        @N.setter
        def N(self, value):
            check_positive_int(value)
            self._N = value

        def check_valid(self):
            if self.fc is None:
                raise ValueError('Critical frequency not specified')

        def to_dict(self):
            dic = {
                'fc': self.fc,
                'N': self.N
                }
            return dic

    @staticmethod
    def _run(trace, params):
        sos = sig.butter(params.N, params.fc, btype='low', output='sos', fs=trace.info.sampling_rate)
        filtered = sig.sosfiltfilt(sos, trace.current)
        # filtered = sig.sosfilt(sos, trace.current)
        new_trace = trace.copy()
        new_trace.current = filtered
        return new_trace

    @classmethod
    def _interactive_gen_params(cls, trace, params):
        while True:
            fc = input_float(
                'Enter critical frequency in Hz',
                pos_only=True,
                default=params.fc
                )
            N = input_int_strict('Enter N', pos_only=True, default=params.N)
            if input_1_safe('Confirm filter parameters?'):
                params.fc = fc
                params.N = N
                break
        return params
