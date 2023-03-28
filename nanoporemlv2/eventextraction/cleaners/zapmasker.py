# -*- coding: utf-8 -*-

from warnings import warn

from pprint import pp

import numpy as np

import matplotlib.pyplot as plt

from ...utils.validators import check_int, check_positive_numeric, check_negative_numeric, check_positive_int
from ...utils.paramcontainer import ParamContainer

from ...interactiveutils.scrollablefig import ScrollableFig
from ...interactiveutils.input_funcs import input_float, input_1_safe, input_1, input_int_strict

from .common import Cleaner

#%%

class ZapMasker(Cleaner):
    name = 'zapmasker'
    class Params(ParamContainer):
        def _init(
                self,
                roll_seconds=0.1,
                positive_zap_threshold=None,
                negative_zap_threshold=-5,
                extra_collateral_damage_rolls=2
                ):

            self.roll_seconds = roll_seconds
            self.positive_zap_threshold = positive_zap_threshold
            self.negative_zap_threshold = negative_zap_threshold
            self.extra_collateral_damage_rolls = extra_collateral_damage_rolls

        @property
        def roll_seconds(self):
            return self._roll_seconds

        @roll_seconds.setter
        def roll_seconds(self, value):
            check_positive_numeric(value)
            if value < 0.01:
                warn(f'Roll shorter than 0.01s')
            self._roll_seconds = float(value)

        @property
        def positive_zap_threshold(self):
            return self._zap_positive_threshold

        @positive_zap_threshold.setter
        def positive_zap_threshold(self, value):
            if value is not None:
                check_positive_numeric(value)
                value = float(value)
            self._zap_positive_threshold = value

        @property
        def negative_zap_threshold(self):
            return self._zap_negative_threshold

        @negative_zap_threshold.setter
        def negative_zap_threshold(self, value):
            if value is not None:
                check_negative_numeric(value)
                value = float(value)
            self._zap_negative_threshold = value

        @property
        def extra_collateral_damage_rolls(self):
            return self._extra_collateral_damage_rolls

        @extra_collateral_damage_rolls.setter
        def extra_collateral_damage_rolls(self, value):
            check_positive_int(value)
            self._extra_collateral_damage_rolls = value

        def check_valid(self):
            if self.positive_zap_threshold is None and self.negative_zap_threshold is None:
                raise ValueError('Neither positive nor negative zap threshold specified')

        def to_dict(self):
            dic = {
                'roll_seconds': self.roll_seconds,
                'positive_zap_threshold': self.positive_zap_threshold,
                'negative_zap_threshold': self.negative_zap_threshold,
                'extra_collateral_damage_rolls': self.extra_collateral_damage_rolls
                }
            return dic

    @staticmethod
    def _run(trace, params):
        roll_samples = trace.info.to_samples(params.roll_seconds)
        shift = int(roll_samples) # Margin of "safety" to gurantee overlap

        pos = None
        if params.positive_zap_threshold:
            pos = trace.current > params.positive_zap_threshold

        neg = None
        if params.negative_zap_threshold:
            neg = trace.current < params.negative_zap_threshold

        if pos is not None and neg is not None:
            mask = pos | neg
        elif neg is None:
            mask = pos
        else:
            mask = neg

        for _ in range(params.extra_collateral_damage_rolls):
            rolled_left = np.roll(mask, -shift)
            rolled_right = np.roll(mask, shift)
            mask = rolled_left | mask | rolled_right

        return trace.masked(mask)

    @classmethod
    def _interactive_gen_params(cls, trace, params):
        sfig1 = ScrollableFig()
        sfig1.plot(trace.time, trace.current)
        plt.title('Original')

        while True:

            if input_1_safe('Any positive zaps?'):
                params.positive_zap_threshold = input_float(
                    'Enter positive threshold for zap acquisition',
                    pos_only=True,
                    default=params.positive_zap_threshold
                    )
            else:
                params.positive_zap_threshold = None

            if input_1_safe('Any negative zaps?'):
                params.negative_zap_threshold = input_float(
                    'Enter negative threshold for zap acquisiion',
                    neg_only=True,
                    default=params.negative_zap_threshold
                    )
            else:
                params.negative_zap_threshold = None

            if params.positive_zap_threshold is None and params.negative_zap_threshold is None:
                if input_1_safe('Neither positive or negative zap threshold specified, abort?'):
                    return None
                else:
                    continue

            params.roll_seconds = input_float(
                'Enter seconds to use for roll',
                pos_only=True,
                default=params.roll_seconds
                )

            params.extra_collateral_damage_rolls = input_int_strict(
                'Enter number of extra collateral damage rolls',
                pos_only=True,
                default=params.extra_collateral_damage_rolls
                )

            masked = cls.run(trace, params)

            sfig2 = ScrollableFig()
            sfig2.plot(masked.time, masked.current)
            plt.title('Masked')

            if input_1_safe('Satisfied with results?'):
                sfig1.close()
                sfig2.close()
                return params
            else:
                sfig2.close()
