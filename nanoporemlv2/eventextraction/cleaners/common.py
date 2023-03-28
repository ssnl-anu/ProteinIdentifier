# -*- coding: utf-8 -*-

from pprint import pp

from ...utils.paramcontainer import ParamContainer

#%%

class Cleaner:
    name = None

    def __init__(self):
        raise RuntimeError('Cleaners are not meant to be initialized')

    @classmethod
    def run(cls, trace, params=None, **kwargs):
        assert issubclass(cls.Params, ParamContainer)

        if params is None:
            params = cls.Params(**kwargs)
        else:
            params = cls.Params(params, **kwargs)
        params.check_valid()

        return cls._run(trace, params)

    @staticmethod
    def _run(trace, params):
        raise NotImplementedError

    class Params(ParamContainer):
        pass

    @classmethod
    def interactive_gen_params(cls, trace, params={}, **kwargs):
        params = cls.Params(params, **kwargs)
        params = cls._interactive_gen_params(trace, params)
        if params is not None:
            pp(params.to_dict())
        return params


    @classmethod
    def _interactive_gen_params(cls, trace, params):
        raise NotImplementedError
