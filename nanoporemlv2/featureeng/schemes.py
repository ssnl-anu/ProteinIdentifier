# -*- coding: utf-8 -*-

import numpy as np
import scipy.signal as sig
import scipy.stats as stats

from ..interactiveutils.input_funcs import make_input_opt

#%%

def geometric_features__(signal, sample_period):
    width = len(signal) * sample_period
    area = sum(signal) * sample_period
    peaks, _ = sig.find_peaks(signal)
    if len(peaks) == 0:
        return [np.nan, np.nan, np.nan, area]
    highest_peak = max(peaks, key=lambda peak: signal[peak])

    height = signal[highest_peak]
    fwhm_, heightatfwhm_, _, _ = sig.peak_widths(signal, [highest_peak], rel_height=0.5)
    fwhm = fwhm_[0] * sample_period
    heightatfwhm = heightatfwhm_[0]


    vector = [height, fwhm, heightatfwhm, area]
    return vector

def geometric_features(signal):
    return geometric_features__(signal.values, signal.trace_info.sampling_period)

#%%

def geometric_features_plus__(signal, sample_period):
    vector = geometric_features__(signal, sample_period)
    skew = stats.skew(signal)
    kurt = stats.kurtosis(signal)
    basewidth = len(signal) * sample_period
    vector += [basewidth, skew, kurt]
    return vector

def geometric_features_plus(signal):
    return geometric_features_plus__(signal.values, signal.trace_info.sampling_period)

#%%

def averaging_sample__(signal, samples=10, return_pts_per_slice=False):
    width = len(signal)
    averages = []
    pts_per_slice = width//samples
    num_left_over = width % samples
    if num_left_over % 2 == 0:
        extras_in_first = num_left_over//2
        extras_in_last = num_left_over//2
    else:
        extras_in_first = num_left_over//2 + 1
        extras_in_last = num_left_over//2

    for i in range(samples):
        if i == 0:
            slice_pts = signal[i*pts_per_slice:i*pts_per_slice+pts_per_slice+extras_in_first]
        if i == samples-1:
            slice_pts = signal[i*pts_per_slice:i*pts_per_slice+pts_per_slice+extras_in_last]
        else:
            slice_pts = signal[i*pts_per_slice:i*pts_per_slice+pts_per_slice]

        averages.append(np.average(slice_pts))

    if return_pts_per_slice:
        return averages + [pts_per_slice]
    else:
        return averages


def averaging_sample_(signal, samples=10):
    return averaging_sample__(signal.values, samples=samples)

def averaging_sample_10(signal):
    return averaging_sample_(signal, 10)

def averaging_sample_50(signal):
    return averaging_sample_(signal, 50)

def averaging_sample_10_wslicesize(signal):
    return averaging_sample__(signal.values, samples=10, return_pts_per_slice=True)

#%%

def averaging_10_wslicesize_wgeometricplus(signal):
    return averaging_sample_10_wslicesize(signal) + geometric_features_plus(signal)

#%%

def full_res__(signal, max_size=200):
    expanded_signal = np.zeros( (max_size, ) )
    expanded_signal[:len(signal)] = signal
    return list(expanded_signal)

def full_res_200(signal):
    return full_res__(signal.values, 200) # For 100kHz

def full_res_20000(signal):
    return full_res__(signal.values, 20_000) # For 10MHz

# def full_res_aligned_(signal, max_size=201):
#     expanded_signal = np.zeros( (max_size,) )
#     expanded_signal[:len(signal)] = signal
#     peaks, _ = sig.find_peaks(signal)
#     if len(peaks) == 0:
#         rolls = int( (max_size-len(signal))// 2 )
#     else:
#         highest_peak = max(peaks, key=lambda peak: signal[peak])
#         center = max_size//2
#         rolls = center-highest_peak
#     out_signal = np.roll(expanded_signal, rolls)
#     return out_signal

#%%

def full_res_200_wgeometricplus(signal):
    return full_res_200(signal) + geometric_features_plus(signal)
    
def full_res_20000_wgeometricplus(signal):
    return full_res_20000(signal) + geometric_features_plus(signal)

#%%


SCHEMES = {
    'geometric_features': geometric_features,
    'geometric_features_plus': geometric_features_plus,
    'averaging_sample_10': averaging_sample_10,
    'averaging_sample_50': averaging_sample_50,
    'averaging_sample_10_wslicesize': averaging_sample_10_wslicesize,
    'averaging_10_wslicesize_wgeometricplus': averaging_10_wslicesize_wgeometricplus,
    'full_res_200': full_res_200,
    'full_res_20000': full_res_20000,
    'full_res_200_wgeometricplus': full_res_200_wgeometricplus,
    'full_res_20000_wgeometricplus': full_res_20000_wgeometricplus
    }

def check_scheme(scheme):
    if scheme not in SCHEMES:
        raise ValueError(f'Invalid scheme: {scheme}; Valid schemes are {list(SCHEMES.keys())}')

input_scheme = make_input_opt(SCHEMES.keys())
