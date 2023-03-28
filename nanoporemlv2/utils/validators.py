# -*- coding: utf-8 -*-

import numpy as np

def check_eq_shape(array1, array2):
    array1_shape = array1.shape
    array2_shape = array2.shape
    if array1_shape != array2_shape:
        raise ValueError(f'Shapes do not match: {array1_shape}, {array2_shape}')

def check_numeric(value):
    if not isinstance(value, (int, float, np.integer, np.floating)):
        raise ValueError(f'Not a number: {value}')

def check_bool(value):
    if not isinstance(value, bool):
        raise ValueError(f'Not a bool: {value}')

def check_int(value):
    if not isinstance(value, (int, np.integer)):
        raise ValueError(f'Not an int: {value}')

def check_positive(number):
    if not number > 0:
        raise ValueError(f'Not positive: {number}')

def check_nonnegative(number):
    if not number >= 0:
        raise ValueError(f'Not non-negative: {number}')

def check_negative(number):
    if not number < 0:
        raise ValueError(f'Not negative: {number}')

def check_positive_numeric(value):
    check_numeric(value)
    check_positive(value)

def check_negative_numeric(value):
    check_numeric(value)
    check_negative(value)

def check_nonnegative_int(value):
    check_int(value)
    check_nonnegative(value)

def check_positive_int(value):
    check_int(value)
    check_positive(value)
