# -*- coding: utf-8 -*-

from pprint import pp

from ...utils.paramcontainer import ParamContainer
from ...utils.convenience import combine_dicts

from ...dataloaders.common import Trace

#%%

class EventExtractor:
    name = None
    def __init__(self, trace, params=None, **kwargs):

        assert issubclass(self.Params, ParamContainer)

        self.trace = trace
        if params is None:
            params = self.Params(**kwargs)
        else:
            params = self.Params(params, **kwargs)
        self.params = params
        self._init()

    @property
    def trace(self):
        return self._trace

    @trace.setter
    def trace(self, tr):
        if not isinstance(tr, Trace):
            raise ValueError(f'Not a trace: {tr}')
        self._trace = tr

    @property
    def params(self):
        return self._params

    @params.setter
    def params(self, obj):
        obj = self.Params(obj)
        self._params = obj

    def _init(self, *args, **kwargs):
        raise NotImplementedError

    @property
    def baseline(self):
        raise NotImplementedError

    def run(self):
        self.params.check_valid()
        return self._run()

    def _run(self):
        raise NotImplementedError

    @property
    def raw_events(self):
        raise NotImplementedError

    @property
    def events(self):
        raise NotImplementedError

    def show_results(self):
        raise NotImplementedError

    class Params(ParamContainer):
        pass

    def interactive_set_params(self):
        raise NotImplementedError

    @classmethod
    def interactive_gen_params(cls, trace, params={}, interactive_trace_size=10_000_000, **kwargs):
        params = cls.Params(params, **kwargs)
        trace = trace[:interactive_trace_size]
        params = cls._interactive_gen_params(trace, params)
        pp(params)
        return params

    @classmethod
    def _interactive_gen_params(self, trace, params):
        raise NotImplementedError
