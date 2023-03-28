# -*- coding: utf-8 -*-

import numpy as np
import bottleneck as bn

#%%

def next_i_after_j_in_indices(indices, j):
    # searchsorted returns the idx where if you insert j into indices at that idx,
    # indices remains sorted

    # Case 1: j not in indices, exists i after j in indices
    #           i.e. j is smaller than largest/last i in indices
    #   idx of i is returned regardless of side mode

    # Case 2: j not in indices, does not exists i after j in indices
    #           i.e. j is larger than largest/last i in indices
    #   OOB idx is returned (len+1) regardless of side mode

    # Case 3: j in indices, exists i after j in indices
    #           i.e. j is not last element of indices
    #   idx of j is returned for side='left'
    #   (idx of j) + 1 is returned for side='right,
    #   i is at (idx of j) + 1
    #   (idx of j) + 1 is not OOB obviously

    # Case 4: j in indices, does not exists i after j in indices
    #           i.e. j is last element of indices
    #   idx of j is returned for side='left'
    #   (idx of j) + 1 for side='right'
    #   (idx of j) + 1 is OOB

    # Use side='right' and check/handle OOB
    # Case 1: returns idx of i
    # Case 2: no i and OOB caught
    # Case 3: returns (idx of j) + 1 which is idx of i
    # Case 4: no i and OOB caught

    idx_of_i_in_indices = np.searchsorted(indices, j, side='right')
    try:
        i = indices[idx_of_i_in_indices]
    except IndexError:
        return None
    return i

def last_i_before_j_in_indices(indices, j):
    # Case 1: j not in indices, exists i before j in indices
    #           i.e. j is smaller than largest/last i in indices
    #   idx returned -1 is idx of i regardless of side mode

    # Case 2: j not in indices, does not exists i before j in indices
    #           i.e. j is larger than largest/last i in indices
    #   idx returned -1 is -1 (underflow) regardless of side mode

    # Case 3: j in indices, exists i before j in indices
    #           i.e. j is not first element of indices
    #   idx returned -1 is idx of i for side='left'
    #   idx returned -2 is idx of i for side='left'
    #   Neither will underflow after minus obviously

    # Case 4: j in indices, does not exists i before j in indices
    #           i.e. j is first element of indices
    #   idx returned -1 is -1 (underflow) for side='left'
    #   idx returned -1 is not -1 for side='right'
    #   idx returned -2 is -1 (underflow) for side='right'

    # Use side='left', -1 and check/handle underflow
    # Case 1: get idx of i
    # Case 2: no i and underflow caught
    # Case 3: get idx of 1
    # Case 4: no i and underflow caught

    idx_of_i_in_indices = np.searchsorted(indices, j, side='left') -1
    if idx_of_i_in_indices == -1:
        return None
    i = indices[idx_of_i_in_indices]
    return i

#%%

def make_odd(num):
    if type(num) != int:
        raise ValueError('Number must be integer')
    if num % 2 == 0:
        return num + 1
    return num

def center_bn_move_result(bn_move_result, window_size):
    if window_size % 2 == 0:
        raise ValueError('Result from using even window size cannot be centered')
    return np.roll(bn_move_result, -window_size//2)

def centered_bn_move_median(a, window, min_count=None, axis=-1):
    if window % 2 == 0:
        raise ValueError('Window size must be odd')
    return center_bn_move_result(bn.move_median(a, window, min_count=min_count, axis=axis), window)

def centered_bn_move_mean(a, window, min_count=None, axis=-1):
    if window % 2 == 0:
        raise ValueError('Window size must be odd')
    return center_bn_move_result(bn.move_mean(a, window, min_count=min_count, axis=axis), window)

def centered_bn_move_std(a, window, min_count=None, axis=-1, ddof=0):
    if window % 2 == 0:
        raise ValueError('Window size must be odd')
    return center_bn_move_result(bn.move_std(a, window, min_count=None, axis=-1, ddof=0), window)
