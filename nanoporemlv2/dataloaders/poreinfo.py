# -*- coding: utf-8 -*-

import os

from ..utils.validators import check_positive_numeric
from ..utils.paramcontainer import ParamContainer
from ..utils.casting import cast_float_or_none

from warnings import warn

import csv

PORE_INFO_DB_FILE = './poreinfo.csv' # REPLACE ME (USE ABSOLUTE PATH)

try:
    PORE_INFO_DB_FILE = os.environ['NANOPOREML_PORE_INFO_DB_FILE']
except KeyError:
    pass


PORE_INFO_DICT = {}

class PoreInfo(ParamContainer):
    def _init(
            self,
            open_pore_conductance=None,
            pore_diameter=None,
            ):
        self.open_pore_conductance = open_pore_conductance
        self.pore_diameter = pore_diameter

    @property
    def open_pore_conductance(self):
        return self._open_pore_conductance

    @open_pore_conductance.setter
    def open_pore_conductance(self, value):
        if value is not None:
            check_positive_numeric(value)
            value = float(value)
            if value < 10:
                warn(f'Small open pore conductance, ensure units is nS not uS: {value}')
        self._open_pore_conductance = value

    @property
    def pore_diameter(self):
        return self._pore_diameter

    @pore_diameter.setter
    def pore_diameter(self, value):
        if value is not None:
            check_positive_numeric(value)
            value = float(value)
            if value < 1:
                warn(f'Small pore diameter, ensure units is nm not um: {value}')
        self._pore_diameter = value

    def to_dict(self):
        dic = {
            'open_pore_conductance': self.open_pore_conductance,
            'pore_diameter': self.pore_diameter
            }
        return dic

    def check_valid(self):
        # Only to used for absolutely required checks
        # Generally dependent code should check individual properties themselves
        # instead of using this method
        if self.open_pore_conductance is None:
            raise ValueError('Open pore conductance not set')


def load_pore_info():
    with open(PORE_INFO_DB_FILE, 'r') as f:
        reader = csv.reader(f)
        header = next(reader)
        rows = [row for row in reader]
        dic = {}
        for row in rows:
            pore_id = row[0]
            dic[pore_id] = PoreInfo(
                open_pore_conductance=float(row[1]),
                pore_diameter=cast_float_or_none(row[2]),
                )
    return dic

PORE_INFO_DICT = load_pore_info()

def reload_pore_info():
    global PORE_INFO_DICT
    new_dic = load_pore_info()
    for key in PORE_INFO_DICT:
        if key not in new_dic:
            PORE_INFO_DICT.pop(key)
    PORE_INFO_DICT.update(new_dic)
