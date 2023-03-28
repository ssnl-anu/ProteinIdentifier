# -*- coding: utf-8 -*-

def combine_dicts(*dicts):
    combined_dict = {}
    for dic in dicts:
        combined_dict.update(dic)
    return combined_dict

def readonly_view(array):
    view = array.view()
    view.flags.writeable = False
    return view
