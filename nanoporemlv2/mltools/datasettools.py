# -*- coding: utf-8 -*-

import math
import numpy as np
import scipy.signal as sig

def copy_dataset(X, y):
    new_X = X.copy()
    new_y = y.copy()
    return new_X, new_y

def nan_rows_removed(X, y):
    bad_rows = np.unique(
        np.argwhere( # Indices of nans
            np.isnan(X)
            )[:, 0] # Just the row part of indices
        ) # Unique rows
    X, y = specific_rows_deleted(X, y, bad_rows)
    return X, y

def specific_rows_deleted(X, y, rows):
    X = np.delete(X, rows, axis=0)
    y = np.delete(y, rows, axis=0)
    return X, y

def combine_datasets_Xy(*Xys):
    if len(Xys) % 2 != 0:
        raise ValueError(f'One or more datasets missing X or y')
    if len(Xys) == 2:
        X, y = Xys
        return X, y

    X_lst = []
    y_lst = []
    for i in range(len(Xys)):
        if i % 2 == 0:
            X = Xys[i]
            X_lst.append(X)
        else:
            y = Xys[i]
            y_lst.append(y)

    combined_X = np.concatenate(X_lst)
    combined_y = np.concatenate(y_lst)
    return combined_X, combined_y

def combine_datasets(*datasets):
    Xys = []
    for dataset in datasets:
        X, y = dataset
        Xys += [X, y]
    return combine_datasets_Xy(*Xys)

def group_by_label(*datasets):
    combined_dataset = combine_datasets(*datasets)
    X, y = combined_dataset
    labels = np.unique(y)
    grouped = {}
    for label in labels:
        ind = y==label
        grouped[label] = (X[ind, :], y[ind])
    return grouped

def summarize_grouped(grouped):
    counts = {}
    for label in grouped.keys():
        counts[label] = len(grouped[label][0])
    return counts

def get_equal_rep_groups(grouped, sampling='sequential'):
    if sampling not in ['sequential', 'random']:
        raise ValueError

    counts = summarize_grouped(grouped)
    min_count = min(counts.values())

    equalrep = {}
    for group, dataset in grouped.items():
        X, y = dataset
        if sampling == 'sequential':
            X_ = X[:min_count, :]
            y_ = y[:min_count]
        elif sampling == 'random':
            ind = np.random.choice(np.arange(len(X)), min_count)
            X_ = X[ind, :]
            y_ = y[ind]
        dataset_ = (X_, y_)
        equalrep[group] = dataset_

    return equalrep


def summarize_datasets(*datasets):
    grouped = group_by_label(*datasets)
    return summarize_grouped(grouped)

def expand_and_center(X):

    #       |
    # 0 1 2 3 4 5 6
    #   |
    # 0 1 2
    #       |
    #     0 1 2 -> Req shift = 2: (6/2) - (2/2) = 3-1 = 2
    #  |
    # 0 1
    #       |
    #      0 1
    #      |
    #     0 1 -> req shift = 2: (6/2) - (1/2) = 3-0.5 = 2.5 -> 2

    #      |
    # 0 1 2 3 4 5
    #   |
    # 0 1 2
    #      |
    #    0 1 2
    #     |
    #   0 1 2 -> Req shift= 1: (5/2) - (2/2) = 2.5-1 = 1.5 -> 1
    #  |
    # 0 1
    #      |
    #     0 1 -> req shift = 2: (5/2) - (1/2) = 2.5-0.5 = 2

    rows, cols = X.shape
    new_cols = 2*cols+1 # Odd i.e. integer center should give better alignment
    center = (new_cols-1)/2
    centered_X = np.zeros( (rows, 2*cols) ) # Need to expand X by 2x min to accomodate centering
    for m in range(rows):
        x = X[m, :]
        peaks, _ = sig.find_peaks(x) # This are indices
        if len(peaks) != 0:
            highest_peak = max(peaks, key=lambda peak: x[peak]) # Also an index
            x_center = highest_peak
        else:
            x_center = (cols-1)/2 # (len(x)-1)/2
        shift = math.floor(center - x_center) # This should always be positive by setup
        centered_X[m, shift:shift+cols] = x # shift:shift+len(x)
        # Equivalent to expanded_X[m, :] = np.roll(expanded_X[m, :], shift)

    return centered_X

def expanded(X, new_width):
    rows, cols = X.shape
    assert new_width >= cols
    expanded_X = np.zeros( (rows, new_width) )
    expanded_X[:,:cols] = X
    return expanded_X
