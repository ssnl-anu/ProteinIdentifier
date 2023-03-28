# -*- coding: utf-8 -*-

import numpy as np
from ..interactiveutils.input_funcs import make_input_opt

def nop(*args, **kwargs):
    pass

STANDARDS = {
    'raw': lambda signal: nop()
    }

def root_G0_dG_nS(signal):
    signal.values = signal.values \
        * signal.trace_info.pore_info.open_pore_conductance \
        / (signal.trace_info.signed_voltage)

    # Take root only on magnitude, i.e. preserve sign
    # Otherwise may give nan in some cases
    negs = signal.values < 0
    signal.values = np.sqrt(np.abs(signal.values))
    signal.values[negs] *= -1

    # Units:
    #   ( nA/V * nS ) ** 0.5 === ( nS * nS ) ** 0.5 === nS

NONRAW_STANDARDS = {
    'root_G0_dG_nS': root_G0_dG_nS
    }
STANDARDS.update(NONRAW_STANDARDS)


def check_standard(standard):
    if standard not in STANDARDS:
        raise ValueError(
            f'Invalid standard: {standard}; Valid standards are {list(STANDARDS.keys())}'
            )
def check_nonraw_standarad(standard):
    if standard not in NONRAW_STANDARDS:
        raise ValueError(
            f'Invalid standard: {standard}; Valid standards are {list(NONRAW_STANDARDS.keys())}'
            )

input_nonraw_standard = make_input_opt(NONRAW_STANDARDS.keys())
input_standard = make_input_opt(STANDARDS.keys())
