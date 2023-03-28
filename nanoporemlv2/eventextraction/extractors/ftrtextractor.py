# -*- coding: utf-8 -*-

from warnings import warn

from pprint import pp

import numpy as np
import bottleneck as bn

import matplotlib.pyplot as plt

from ...utils.validators import check_int, check_positive_numeric, check_negative_numeric, check_positive_int
from ...utils.paramcontainer import ParamContainer
from ...utils.convenience import readonly_view

from ...interactiveutils.input_funcs import input_float, input_1_safe
from ...interactiveutils.scrollablefig import ScrollableFig


from ..utils import make_odd, centered_bn_move_median
from ..utils import next_i_after_j_in_indices, last_i_before_j_in_indices

from ..filters import min_max_filt

from ..events import Events

from .common import EventExtractor

#%%

class FTRTExtractor(EventExtractor):
    name = 'ftrtextractor'

    def _init(self):
        if self.trace.info.sampling_period is None:
            raise ValueError
        if self.trace.info.peaks_not_dips is None:
            raise ValueError
        if self.trace.info.max_event_width_seconds is None:
            raise ValueError
        if self.trace.info.min_event_width_seconds is None:
            raise ValueError

        if self.trace.info.peaks_not_dips:
            shift_base = lambda base, shift: base + shift
            above_threshold = lambda val, thresh: val > thresh
            below_threshold = lambda val, thresh: val < thresh
        else:
            shift_base = lambda base, shift: base - shift
            above_threshold = lambda val, thresh: val < thresh
            below_threshold = lambda val, thresh: val > thresh
        self.shift_base = shift_base
        self.above_threshold = above_threshold
        self.below_threshold = below_threshold

        self._baseline = None
        self._std = None
        self._trig_line = None
        self._start_line = None
        self._end_line = None
        self._trigger_indices = None
        self._start_indices = None
        self._end_indices = None
        self._raw_events = None
        self._events = None

    @property
    def baseline_window_size(self):
        return make_odd(int(self.params.baseline_window_scale*self.trace.info.max_event_width_samples))

    def gen_baseline(self):
        self._baseline = centered_bn_move_median(self.trace.current, self.baseline_window_size)

    @property
    def baseline(self):
        return self._baseline

    @property
    def std_window_size(self):
        return make_odd(int(self.params.std_window_scale*self.trace.info.max_event_width_samples))

    @property
    def std_smoothing_window_size(self):
        return make_odd(int(self.params.std_smoothing_scale_factor*self.std_window_size))

    def gen_std(self):
        if self.baseline is None:
            self.gen_baseline()
        self._presmoothing_std = bn.move_std(self.trace.current - self.baseline, self.std_window_size)
        self._std = centered_bn_move_median(self._presmoothing_std, self.std_smoothing_window_size)
        self._std_line = self.shift_base(self.baseline, self.std)

    @property
    def std(self):
        return self._std

    @property
    def std_line(self):
        return readonly_view(self._std_line[:])

    def gen_trig_line(self):
        if self.baseline is None:
            self.gen_baseline()
        if self.std is None:
            self.gen_std()
        self._trig_line = self.shift_base(self.baseline, self.params.trig_std*self.std)

    @property
    def trig_line(self):
        return self._trig_line

    def gen_start_line(self):
        if self.baseline is None:
            self.gen_baseline()
        if self.std is None:
            self.gen_std()
        self._start_line = self.shift_base(self.baseline, self.params.start_std*self.std)

    @property
    def start_line(self):
        return self._start_line

    def gen_end_line(self):
        if self.baseline is None:
            self.gen_baseline()
        if self.std is None:
            self.gen_std()
        self._end_line = self.shift_base(self.baseline, self.params.end_std*self.std)

    @property
    def end_line(self):
        return readonly_view(self._end_line)

    def identify_events(self):
        if self.trig_line is None:
            self.gen_trig_line()
        if self.start_line is None:
            self.gen_start_line()
        if self.end_line is None:
            self.gen_end_line()

        self._triggers = self.above_threshold(self.trace.current, self.trig_line)
        self._starts = self.below_threshold(self.trace.current, self.start_line)
        self._ends = self.below_threshold(self.trace.current, self.end_line)

        # Keep local handle for performance reasons
        trigger_indices = np.nonzero(self.triggers)[0]
        start_indices = np.nonzero(self.starts)[0]
        end_indices = np.nonzero(self.ends)[0]

        self._trigger_indices = trigger_indices
        self._start_indices = start_indices
        self._end_indices = end_indices

        i = 0
        triggered = False
        events = []
        event = None
        while True:
            if not triggered:
                i = next_i_after_j_in_indices(trigger_indices, i)
                if i is None:
                    break
                triggered = True
                start = last_i_before_j_in_indices(start_indices, i)
                if start is None: # Unlikely to occur but just in case e.g. huge jump in 1 sample or something
                    triggered = False
                    continue
                event = [start]

            if triggered:
                i_ = next_i_after_j_in_indices(end_indices, i)
                if i_ is not None:
                    i = i_
                    end = i+1
                    event.append(end)
                    events.append(event)
                triggered = False
                event = None
        self._raw_events = events
        self._events = Events.init_from_extractor(self)
        # self._events = Events([Event(self.trace, self.baseline, start, end) for start, end in events])

    @property
    def triggers(self):
        return readonly_view(self._triggers)

    @property
    def starts(self):
        return readonly_view(self._starts)

    @property
    def ends(self):
        return readonly_view(self._ends)

    @property
    def trigger_indices(self):
        return readonly_view(self._trigger_indices)

    @property
    def start_indices(self):
        return readonly_view(self._start_indices)

    @property
    def end_indices(self):
        return readonly_view(self._end_indices)

    @property
    def raw_events(self):
        return self._raw_events

    def filter_events(self):
        '''
        Safety net filtering
        '''
        self._events = self._events.filtered(
            lambda event: min_max_filt(
                event,
                self.trace.info.min_event_width_samples,
                self.trace.info.max_event_width_samples
                )
            )

    @property
    def events(self):
        return self._events

    def _run(self):
        self.gen_baseline()
        self.gen_std()
        self.gen_trig_line()
        self.gen_start_line()
        self.gen_end_line()
        self.identify_events()
        self.filter_events()
        return self.events

    def show_results(self):
        sfig = ScrollableFig()
        sfig.plot(self.trace.time, self.trace.current, color='grey', label='Data')
        if self.baseline is not None:
            sfig.plot(self.trace.time, self.baseline, color='blue', alpha=0.75, label='Baseline')
        if self.trig_line is not None:
            sfig.plot(self.trace.time, self.trig_line, color='red', alpha=0.5, label='Trigger')
        if self.start_line is not None:
            sfig.plot(self.trace.time, self.start_line, color='green', alpha=0.5, label='Start')
        if self.end_line is not None:
            sfig.plot(self.trace.time, self.end_line, color='teal', alpha=0.5, label='End')
        if self.events is not None:
            is_event = np.zeros_like(self.trace.current)
            for event in self.events:
                is_event[event.as_slice()] = 1
            if not self.trace.info.peaks_not_dips:
                is_event = is_event*-1
            is_event = is_event*(10*bn.nanstd(self.trace.current[:1000]))
            is_event += bn.nanmax(self.trace.current[:1000])
            sfig.plot(self.trace.time, is_event, color='orange', alpha=0.5, label='Event?')
        plt.legend(loc='upper right')
        return sfig

    class Params(ParamContainer):
        def _init(
                self,
                baseline_window_scale=3,
                std_window_scale=3,
                std_smoothing_scale_factor=2,
                trig_std=6,
                start_std=0.75,
                end_std=0.5
                ):

            self.baseline_window_scale = baseline_window_scale
            self.std_window_scale = std_window_scale
            self.std_smoothing_scale_factor = std_smoothing_scale_factor
            self.trig_std = trig_std
            self.start_std = start_std
            self.end_std = end_std

        @property
        def baseline_window_scale(self):
            return self._baseline_window_scale

        @baseline_window_scale.setter
        def baseline_window_scale(self, value):
            check_positive_numeric(value)
            self._baseline_window_scale = float(value)

        @property
        def std_window_scale(self):
            return self._std_window_scale

        @std_window_scale.setter
        def std_window_scale(self, value):
            check_positive_numeric(value)
            self._std_window_scale = float(value)

        @property
        def std_smoothing_scale_factor(self):
            return self._std_smoothing_scale_factor

        @std_smoothing_scale_factor.setter
        def std_smoothing_scale_factor(self, value):
            check_positive_numeric(value)
            if value < 2.0:
                warn(f'Stdev smoothing scale factor smaller than recommended of at least 2.0: {value}')
            self._std_smoothing_scale_factor = float(value)

        @property
        def trig_std(self):
            return self._trig_std

        @trig_std.setter
        def trig_std(self, value):
            check_positive_numeric(value)
            if value < 5.0:
                warn(f'Trigger threshold is set to smaller than 5.0 stdevs: {value}')
            self._trig_std = float(value)

        @property
        def start_std(self):
            return self._start_std

        @start_std.setter
        def start_std(self, value):
            check_positive_numeric(value)
            if value > 3:
                warn(f'Event start crossing line is set to above 3 stdevs: {value}')
            self._start_std = float(value)

        @property
        def end_std(self):
            return self._end_std

        @end_std.setter
        def end_std(self, value):
            check_positive_numeric(value)
            if value > 3:
                warn(f'Event end crossing line is set to above 3 stdevs: {value}')
            self._end_std = value

        def check_valid(self):
            pass

        def to_dict(self):
            dic = {
                'baseline_window_scale': self.baseline_window_scale,
                'std_window_scale': self.std_window_scale,
                'std_smoothing_scale_factor': self.std_smoothing_scale_factor,
                'trig_std': self.trig_std,
                'start_std': self.start_std,
                'end_std': self.end_std
                }
            return dic

    @classmethod
    def _interactive_gen_params(cls, trace, params):
        extractor = cls(trace, params)
        while True:
            print(f'Base window size is {trace.info.max_event_width_seconds}s')
            sfig = ScrollableFig()
            sfig.plot(trace.time, trace.current, color='grey', label='Data')
            plt.legend(loc='upper right')
            while True:
                extractor.params.baseline_window_scale = input_float(
                    'Enter baseline window scale',
                    pos_only=True,
                    default=extractor.params.baseline_window_scale
                    )
                print(f'Baseline window size is {extractor.baseline_window_size} samples')
                extractor.gen_baseline()
                sfig.plot(trace.time, extractor.baseline, color='blue', alpha=0.75, label='Baseline')
                if input_1_safe(f'Accept baseline?'):
                    break
                else:
                    sfig.remove_last_line()

            while True:
                extractor.params.std_window_scale = input_float(
                    'Enter std window scale',
                    pos_only=True,
                    default=extractor.params.std_window_scale
                    )
                print(f'Std window size is {extractor.std_window_size} samples')
                extractor.params.std_smoothing_scale_factor = input_float(
                    'Enter std smoothing scale factor',
                    pos_only=True,
                    default=extractor.params.std_smoothing_scale_factor
                    )
                extractor.gen_std()
                sfig.plot(trace.time, extractor.std_line, color='magenta', alpha=0.5, label='Std')
                if input_1_safe(f'Accept std?'):
                    break
                else:
                    sfig.remove_last_line()

            while True:
                extractor.params.trig_std = input_float(
                    'Enter trigger threshold in units of stds',
                    pos_only=True,
                    default=extractor.params.trig_std
                    )
                extractor.gen_trig_line()
                sfig.plot(trace.time, extractor.trig_line, alpha=0.5,
                          label=f'Trigger ({extractor.params.trig_std}std)'
                          )
                if input_1_safe('Confirm trigger threshold?'):
                    break
                else:
                    sfig.remove_last_line()

            while True:
                extractor.params.start_std = input_float(
                    'Enter start threshold in units of stds',
                    pos_only=True,
                    default=extractor.params.start_std
                    )
                extractor.gen_start_line()
                sfig.plot(trace.time, extractor.start_line, alpha=0.5,
                          label=f'Start ({extractor.params.start_std}std)'
                          )
                if input_1_safe('Confirm start line placement?'):
                    break
                else:
                    sfig.remove_last_line()

            while True:
                extractor.params.end_std = input_float(
                    'Enter end threshold in units of stds',
                    pos_only=True,
                    default=extractor.params.end_std
                    )
                extractor.gen_end_line()
                sfig.plot(trace.time, extractor.end_line, alpha=0.5,
                          label=f'End ({extractor.params.end_std}std)'
                          )
                if input_1_safe('Confirm end line placement?'):
                    break
                else:
                    sfig.remove_last_line()

            sfig.close()
            extractor.identify_events()
            extractor.filter_events()
            sfig = extractor.show_results()
            if input_1_safe('Happy with results?'):
                sfig.close()
                return extractor.params
            else:
                sfig.close()
                continue
