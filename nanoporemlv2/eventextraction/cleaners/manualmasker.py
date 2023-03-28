# -*- coding: utf-8 -*-

from warnings import warn

from pprint import pp

import numpy as np

import matplotlib.pyplot as plt

from ...utils.validators import check_nonnegative_int, check_positive_int
from ...utils.paramcontainer import ParamContainer

from ...interactiveutils.scrollablefig import ScrollableFig
from ...interactiveutils.input_funcs import input_1, input_1_safe

from .common import Cleaner

#%%

class ManualMasker(Cleaner):
    name = 'manualmasker'

    class Params(ParamContainer):
        def _init(
                self,
                slices=[]
                ):

            self._slices = []
            for slce in slices:
                self.add_slice(*slce)

        @property
        def slices(self):
            return self._slices[:]

        def add_slice(self, slice_start, slice_end):
            check_nonnegative_int(slice_start)
            check_nonnegative_int(slice_end)
            if slice_start > slice_end:
                raise ValueError('Slice start is after slice end: {slice_start}:{slice_end}')
            self._slices.append( (slice_start, slice_end) )

        def remove_slice(self, slice_start, slice_end):
            slce = (slice_start, slice_end)
            if slce not in self._slices:
                raise KeyError(f'Slice not in slices: {slce}')
            self._slices.remove(slce)

        def check_valid(self):
            pass

        def to_dict(self):
            dic = {
                'slices': self.slices
                }
            return dic

    @staticmethod
    def _run(trace, params):
        new_trace = trace.copy()
        for slice_start, slice_end in params.slices:
            new_trace.apply_mask(slice(slice_start, slice_end))
        return new_trace

    @classmethod
    def _interactive_gen_params(cls, trace, params):
        sfig_orig = ScrollableFig()
        sfig_orig.plot(trace.time, trace.current)
        plt.title('Original')

        length = len(trace)

        new_trace = trace.copy()
        sfig_new = ScrollableFig()
        sfig_new.plot(new_trace.time, new_trace.current)
        plt.title('Masked')

        for start, end in params.slices:
            slice_size = end - start

            if end > length:
                warn(f'Truncating out of bounds end to length of trace: {end} -> {length}')
                end = length

            sfig_orig.view_end = end
            if sfig_orig.view_size < slice_size:
                sfig_orig.view_size = slice_size
            sfig_new.sync_view(sfig_orig)

            values = new_trace.current[start:end].copy()
            new_trace.current[start:end] = np.nan
            sfig_new.update_lines()

            if not input_1_safe('Keep this part masked?'):
                new_trace.current[start:end] = values
                sfig_new.update_lines()
                params.remove_slice(start, end)

        while True:
            if input_1_safe('Mask more? If yes, adjust view of figure with title "Masked" to exactly region to be cut before responding'):
                start = sfig_new.view_start
                end_ = sfig_new.view_end

                end = end_
                if end > length:
                    end = length

                sfig_orig.sync_view(sfig_new)

                values = new_trace.current[start:end].copy()
                new_trace.current[start:end] = np.nan

                sfig_new.update_lines()

                if not input_1_safe('Accept masking of this part?'):
                    new_trace.current[start:end] = values
                    sfig_new.update_lines()
                else:
                    params.add_slice(start, end)
                    print(f'Added to masking: ({start}, {end})')
            else:
                if len(params.slices) == 0:
                    if input_1_safe('No slices selected, abort?'):
                        params = None
                    else:
                        continue
                break

        sfig_orig.close()
        sfig_new.close()

        return params
