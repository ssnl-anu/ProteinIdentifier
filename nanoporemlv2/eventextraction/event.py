# -*- coding: utf-8 -*-

import math

from pathlib import Path
from zipfile import ZipFile

import numpy as np
import matplotlib.pyplot as plt

from ..utils.casting import cast_1d_nonempty_numeric_array
from ..utils.validators import check_nonnegative_int, check_eq_shape
from ..utils.convenience import readonly_view

from ..dataloaders.common import Trace, Info

from ..signal.signal import Signal

#%%

# This class needs to be relatively high performance
# Avoid copying unless absolutely necessary
# Ok to do validation though
class Event:
    def __init__(self, trace, baseline, start, end):
        if not isinstance(trace, Trace):
            raise ValueError(f'Not a trace: {trace}')
        self._trace = trace
        self.baseline = baseline
        self.set_start_end(start, end)

    @property
    def trace_info(self):
        return self._trace.info

    @property
    def current(self):
        return self._trace.current

    @property
    def time(self):
        return self._trace.time

    def __getitem__(self, key):
        if key == 0:
            return self.start
        elif key == 1:
            return self.end
        else:
            raise IndexError()

    def __str__(self):
        return f'[{self.start}, {self.end}]'

    def __repr__(self):
        return f'<Event [{self.start}, {self.end}]>'

    # @property
    # def trace(self):
    #     return self._trace

    @property
    def baseline(self):
        return self._baseline

    @baseline.setter
    def baseline(self, array_like):
        self._baseline = cast_1d_nonempty_numeric_array(array_like)

    @property
    def start(self):
        return self._start

    @start.setter
    def start(self, value):
        check_nonnegative_int(value)
        if value >= self.end:
            raise ValueError(f'Start same as or after end: {value}')
        self._start = value

    @property
    def end(self):
        return self._end

    @end.setter
    def end(self, value):
        check_nonnegative_int(value)
        if value <= self.start:
            raise ValueError(f'End same as or before start: {value}')
        self._end = value

    def set_start_end(self, start, end):
        check_nonnegative_int(start)
        check_nonnegative_int(end)
        if start >= end:
            raise ValueError('Start same as or after end: {start}, {end}')
        self._start = start
        self._end = end

    @property
    def start_time(self):
        return self.time[self._start]

    @property
    def end_time(self):
        return self.time[self._end-1]

    def _calc_expanded_start_end(self, expand):
        start = max(0, self.start-expand)
        end = self.end + expand
        return start, end

    def _gen_view(self, seq, expand=0, readonly=True):
        check_nonnegative_int(expand)
        start, end = self._calc_expanded_start_end(expand)
        view = seq[start:end]
        if readonly:
            view = readonly_view(view)
        return view

    def view_current(self, expand=0):
        return self._gen_view(self.current, expand=expand, readonly=True)

    def view_baseline(self, expand=0):
        return self._gen_view(self.baseline, expand=expand, readonly=False)

    def view_time(self, expand=0):
        return self._gen_view(self.time, expand=expand, readonly=True)

    def __len__(self):
        return self.end - self.start

    def as_slice(self):
        return slice(self.start, self.end)

    def to_signal(self):
        if self.trace_info.peaks_not_dips:
            values = self.view_current() - self.view_baseline()
        else:
            values = self.view_baseline() - self.view_current()
        # Note: The above is not a view
        signal = Signal(values, trace_info=self.trace_info)
        signal._standard = 'raw'
        return signal

    def show(self, expand=0, ax=None):
        if ax is None:
            ax = plt.gca()
        time = self.view_time(expand=expand)
        current = self.view_current(expand=expand)
        baseline = self.view_baseline(expand=expand)
        ax.plot(time, current, color='grey', label='Data')
        ax.plot(time, baseline, color='blue', label='Baseline')
        if expand != 0:
            ax.vlines(
                [self.start_time, self.end_time], min(current), max(current),
                color='k', linestyle='--', label='Event boundaries')
        ax.legend()

    def to_portable(self, no_check=False):
        if not no_check:
            self.trace_info.check_valid() # Enforce complete and valid trace info before saving
        expand = max(2*len(self), 2*self.trace_info.min_event_width_samples)
        capture_start, capture_end = self._calc_expanded_start_end(expand)
        rel_event_start = self.start - capture_start
        rel_event_end = self.end - capture_start
        return PortableEvent(
            self.trace_info,
            self.view_current(expand),
            self.view_time(expand),
            self.view_baseline(expand),
            rel_event_start,
            rel_event_end,
            self.start,
            self.end,
            no_check=True
            )

#%%

class PortableEvent(Event):
    def __init__(self,
                 trace_info,
                 current,
                 time,
                 baseline,
                 rel_start,
                 rel_end,
                 orig_start,
                 orig_end,
                 no_check=False
                 ):
        if not no_check:
            trace_info = Info(trace_info)
            trace_info.check_valid()
            current = cast_1d_nonempty_numeric_array(current)
            time = cast_1d_nonempty_numeric_array(time)
            baseline = cast_1d_nonempty_numeric_array(baseline)
            check_eq_shape(current, time)
            check_eq_shape(current, baseline)

        self._trace_info = trace_info

        self._current = current
        self._time = time
        self._baseline = baseline

        self.set_start_end(orig_start, orig_end) # Check them only
        self._orig_start = orig_start
        self._orig_end = orig_end

        self.set_start_end(rel_start, rel_end) # Check and set

        self._trace = None

    @property
    def trace_info(self):
        return self._trace_info

    @property
    def current(self):
        return readonly_view(self._current)

    @property
    def time(self):
        return readonly_view(self._time)

    @property
    def baseline(self):
        return self._baseline

    def to_portable(self):
        raise NameError('Already portable!')

    @property
    def orig_start(self):
        return self._orig_start

    @property
    def orig_end(self):
        return self._orig_end

    def as_orig_slice(self):
        return slice(self.orig_start, self.orig_end)

    def __repr__(self):
        return f'<PortableEvent [{self.start}, {self.end}]>'
