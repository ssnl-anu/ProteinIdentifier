# -*- coding: utf-8 -*-

from .convenience import combine_dicts

import json

import copy

from pathlib import Path

class ParamContainer:

    def __init__(self, params={}, **kwargs):
        if isinstance(params, ParamContainer):
            dic = params.to_dict()
        else:
            dic = dict(params)
        self._init(**combine_dicts(dic, kwargs))

    def _init(self, *args, **kwargs):
        raise NotImplementedError

    def to_dict(self):
        raise NotImplementedError

    def to_json(self):
        return json.dumps(self.to_dict(), indent=2)

    def to_json_file(self, path, overwrite=False):
        mode = 'x'
        if overwrite == True:
            mode = 'w'
        with open(path, mode) as f:
            json.dump(self.to_dict(), f, indent=2)

    def check_valid(self):
        raise NotImplementedError

    def copy(self):
        return copy.copy(self)

    def __str__(self):
        return self.to_dict().__str__()

    def __repr__(self):
        return '{}({})'.format(
            self.__class__.__name__,
            self.to_dict()
            )

    @classmethod
    def from_json(cls, json_str):
        dic = json.loads(json_str)
        for key in dic.keys():
            if not isinstance(key, str):
                raise ValueError('Corrupted or invalid params json')
            if key[0] == '_':
                dic.pop(key) # Ignore conventional comments
        return cls(dic)

    @classmethod
    def from_json_file(cls, path):
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f'File does not exist: {path}')
        if not path.is_file():
            raise IsADirectoryError(f'Not a file: {path}')
        dic = json.load(path.open('r'))
        return cls(dic)
