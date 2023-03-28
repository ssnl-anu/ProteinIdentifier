#

__all__ = [
    "common", "pore_info",
    "abf", "advantestdata"
    ]

#%%

LABELS = [
    'DNA',
    'BSA',
    'ConA',
    'BovineHb',
    'HSA',
    'BSA_HSA_5050',
    'BSA_HSA_7525',
    'BSA_HSA_2575',
    'BSA_HSA_ConA_1_1_1',
    'BSA_BovineHb_5050',
    'BSA_BovineHb_7525'
    ]

from ..interactiveutils.input_funcs import make_input_opt

input_label = make_input_opt(LABELS)

#%%

from .abf import ABF

DATALOADERS = [ABF]
DATALOADERS = {dataloader.name: dataloader for dataloader in DATALOADERS}
