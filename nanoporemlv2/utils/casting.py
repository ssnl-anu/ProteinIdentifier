# -*- coding: utf-8 -*-

import numpy as np

def cast_1d_nonempty_numeric_array(array_like):
    if isinstance(array_like, np.ndarray):
        array = array_like
    else:
        array = np.array(array_like)
    shape = array.shape
    if len(shape) > 1:
        raise ValueError(f'Shape not 1D: {shape}')
    if shape[0] == 0:
        raise ValueError('Array is empty')
    dtype_kind = array.dtype.kind
    if dtype_kind not in 'if':
        raise ValueError(f'Invalid dtype: {dtype_kind}')
    return array

def cast_float_or_none(val):
    try:
        return float(val)
    except TypeError:
        return None
