# -*- coding: utf-8 -*-

from pprint import pp

import matplotlib.pyplot as plt

from ...utils.validators import check_nonnegative_int, check_positive_int
from ...utils.paramcontainer import ParamContainer

from ...interactiveutils.scrollablefig import ScrollableFig
from ...interactiveutils.input_funcs import input_int_strict, input_1_safe, input_1_default

from .common import Cleaner

#%%

class Trimmer(Cleaner):
    name = 'trimmer'

    class Params(ParamContainer):
        def _init(
                self,
                slice_start=0,
                slice_end=None
                ):

            self.slice_start = slice_start
            self.slice_end = slice_end

        @property
        def slice_start(self):
            return self._slice_start

        @slice_start.setter
        def slice_start(self, value):
            check_nonnegative_int(value)
            self._slice_start = int(value)

        @property
        def slice_end(self):
            return self._slice_end

        @slice_end.setter
        def slice_end(self, value):
            if value is not None:
                check_positive_int(value)
                value = int(value)
            self._slice_end = value

        def check_valid(self):
            if (self.slice_end is not None) and (self.slice_start >= self.slice_end):
                raise ValueError('Slice start is not before slice end: {self.slice_start}:{self.slice_end}')

        def to_dict(self):
            dic = {
                'slice_start': self.slice_start,
                'slice_end': self.slice_end
                }
            return dic

    @staticmethod
    def _run(trace, params):
        return trace[params.slice_start:params.slice_end]

    @classmethod
    def _interactive_gen_params(cls, trace, params):
        sfig1 = ScrollableFig()
        sfig1.plot(trace.time, trace.current)
        plt.title('Original')

        while True:
            params.slice_start = input_int_strict(
                'Enter slice start',
                pos_only=True,
                zero_ok=True,
                default=params.slice_start
                )

            if input_1_default('Does end need trimming?', default=params.slice_end is not None):
                while True:
                    params.slice_end = input_int_strict(
                        'Enter slice end',
                        pos_only=True,
                        zero_ok=False,
                        default=params.slice_end
                        )

                    if params.slice_end <= params.slice_start:
                        print('Slice end before slice start')
                        continue
                    break

            trimmed = cls.run(trace, params)
            sfig2 = ScrollableFig()
            sfig2.plot(trimmed.time, trimmed.current)
            plt.title('Trimmed')

            if input_1_safe('Accept trim?'):
                if params.slice_start == 0 and params.slice_end == len(trace):
                    if input_1_safe('Trim selected is equivalent to no trim, abort?'):
                        params = None
                    else:
                        sfig2.close()
                        continue
                sfig1.close()
                sfig2.close()
                return params
            else:
                sfig2.close()
