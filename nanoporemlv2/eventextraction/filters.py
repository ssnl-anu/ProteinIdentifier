# -*- coding: utf-8 -*-

def min_filt(event, min_width_samples):
    if len(event) > min_width_samples:
        return True

def max_filt(event, max_width_samples):
    if len(event) <= max_width_samples:
        return True

def min_max_filt(event, min_width_samples, max_width_samples):
    if min_width_samples < len(event) <= max_width_samples:
        return True
