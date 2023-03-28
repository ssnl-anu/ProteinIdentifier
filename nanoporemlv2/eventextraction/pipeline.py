# -*- coding: utf-8 -*-

from warnings import warn

from pprint import pp

import matplotlib.pyplot as plt

from ..utils.validators import check_int
from ..utils.paramcontainer import ParamContainer

from ..interactiveutils.scrollablefig import ScrollableFig
from ..interactiveutils.input_funcs import input_1_safe, make_input_opt

from ..dataloaders.common import Trace, Info

from .cleaners import CLEANERS
from .extractors import EVENTEXTRACTORS, input_eventextractor


#%%

class EventExtractionPipeline:
    def __init__(self, trace, settings=None):
        self.trace = trace
        self.settings = settings
        self._orig_trace = trace
        self._eventextractor = None
        self._events = None

    @property
    def trace(self):
        return self._trace

    @trace.setter
    def trace(self, obj):
        if not isinstance(obj, Trace):
            raise ValueError(f'Not a trace: {type(obj)}')
        self._trace = obj
        self._orig_trace = obj

    @property
    def settings(self):
        return self._settings

    @settings.setter
    def settings(self, obj):
        if obj is None:
            self._settings = Settings()
        else:
            self._settings = Settings(obj)
        # if self._settings.trace_info is not None:
        #     self.trace.info = self._settings.trace_info

    def run(self):
        self.settings.check_valid()
        if self.settings.trace_info is not None:
            self.trace.info = self.settings.trace_info
        else:
            self.trace.info.check_valid()
        self.clean()
        self.extract()

    def clean(self):
        self._orig_trace = self.trace
        for cleaner in self.settings.cleaners:
            self._trace = CLEANERS[cleaner].run(
                self._trace,
                self.settings.cleaner_params[cleaner]
                )

    @property
    def orig_trace(self):
        return self._orig_trace

    def extract(self):
        self._eventextractor = EVENTEXTRACTORS[self.settings.eventextractor](
            self.trace,
            self.settings.eventextractor_params[self.settings.eventextractor]
            )
        self._events = self._eventextractor.run()
        self._events._extracted_from = self

    @property
    def events(self):
        return self._events # This is just a reference to self.eventextractor.events

    @classmethod
    def interactive_gen_settings(cls, trace, prefill_settings=None, **kwargs):
        pipeline = cls(trace, prefill_settings, **kwargs)

        while True:
            if pipeline.settings.trace_info is not None:
                pipeline.trace.info = pipeline.settings.trace_info

            pipeline.trace.interactive_fill_info()
            pipeline.settings.trace_info = pipeline.trace.info

            sfig = ScrollableFig()
            sfig.plot(trace.time, trace.current)
            plt.title('Original Original')

            configure_cleaning = True

            try:
                pipeline.settings.check_cleaner_settings()
            except Exception:
                print('Existing cleaner settings invalid, ignoring existing cleaners selection')
                pipeline.settings.cleaners = []


            if len(pipeline.settings.cleaners) != 0:
                print(f'Existing cleaners settings:')
                for i, cleaner in enumerate(pipeline.settings.cleaners):
                    print(f'\t{i} {cleaner}')
                    print(f'\t\t{pipeline.settings.cleaner_params[cleaner]}')
                pipeline.clean()

                sfig1 = ScrollableFig()
                sfig1.plot(pipeline.trace.time, pipeline.trace.current)
                plt.title('Cleaned')

                if input_1_safe('Happy with existing cleaning settings?'):
                    configure_cleaning = False
                else:
                    pipeline.settings.cleaners = []
                    pipeline.trace.current = trace.current
                    pipeline.trace.time = trace.time
                sfig1.close()

            else:
                configure_cleaning = input_1_safe('Does trace need cleaning?')

            if configure_cleaning:
                cleaned = pipeline.trace
                while True:
                    choices = [cleaner for cleaner in CLEANERS if cleaner not in pipeline.settings.cleaners] + ['DONE']
                    input_choice = make_input_opt(choices)
                    choice = input_choice('Choose cleaner to add')

                    if choice == 'DONE':
                        break
                    cleaner = choice

                    if cleaner in pipeline.settings.cleaner_params:
                        params = pipeline.settings.cleaner_params[cleaner]
                    else:
                        params = {}

                    params = CLEANERS[cleaner].interactive_gen_params(
                        cleaned,
                        params
                        )

                    if params is None:
                        print('Cleaner not added as cleaner params generation aborted')
                        continue

                    cleaned = CLEANERS[cleaner].run(cleaned, params)

                    pipeline.settings.append_cleaner(cleaner)
                    pipeline.settings.update_cleaner_params({cleaner: params})
                pipeline.trace = cleaned

            sfig.close()

            while True:
                eventextractor = input_eventextractor(
                    'Select event extractor',
                    default=pipeline.settings.eventextractor
                    )
                if input_1_safe(f'Confirm use {eventextractor} for event extraction?'):
                    pipeline.settings.eventextractor = eventextractor
                    break

            if eventextractor in pipeline.settings.eventextractor_params:
                eventextractor_params = pipeline.settings.eventextractor_params[eventextractor]
            else:
                eventextractor_params = {}

            eventextractor_params =  EVENTEXTRACTORS[eventextractor].interactive_gen_params(
                pipeline.trace,
                eventextractor_params
                )

            pipeline.settings.update_eventextractor_params({eventextractor: eventextractor_params})

            if input_1_safe('Happy with settings?'):
                break

        pp(pipeline.settings.to_dict())
        return pipeline.settings

    def interactive_run(self):
        self._settings = self.interactive_configure(self.trace)
        self.run()

#%%

class Settings(ParamContainer):
    def _init(
            self,
            trace_info=None,
            cleaners=[],
            cleaner_params={},
            eventextractor=None,
            eventextractor_params={}
            ):
        self.trace_info = trace_info
        self.cleaners = cleaners
        self.cleaner_params = cleaner_params
        self.eventextractor = eventextractor
        self.eventextractor_params = eventextractor_params

    @property
    def trace_info(self):
        return self._trace_info

    @trace_info.setter
    def trace_info(self, info):
        if info is not None:
            info = Info(info)
        self._trace_info = info

    @property
    def cleaners(self):
        return self._cleaners[:]

    @cleaners.setter
    def cleaners(self, lst):
        for key in lst:
            if key not in CLEANERS.keys():
                raise KeyError(f'Invalid cleaner: {key}')
        self._cleaners = lst[:]

    def insert_cleaner(self, cleaner, index):
        check_int(index)
        if cleaner not in CLEANERS.keys():
            raise KeyError(f'Invalid cleaner: {cleaner}')
        self._cleaners.insert(index, cleaner)

    def append_cleaner(self, cleaner):
        self.insert_cleaner(cleaner, len(self._cleaners))

    def pop_cleaner(self, index):
        check_int(index)
        return self._cleaners.pop(index)

    @property
    def cleaner_params(self):
        return self._cleaner_params.copy() # shallow is intended

    @cleaner_params.setter
    def cleaner_params(self, dic_of_params):
        if not isinstance(dic_of_params, dict):
            raise ValueError(f'Not a dict: {dic_of_params}')

        dic_of_params = dic_of_params.copy()

        for cleaner, params in dic_of_params.items():
            if cleaner not in CLEANERS:
                raise KeyError(f'Invalid cleaner: {cleaner}')
            if cleaner not in self._cleaners:
                warn(f'Cleaner not added yet: {cleaner}')

            params = CLEANERS[cleaner].Params(params) # Dont catch this

            dic_of_params[cleaner] = params

        self._cleaner_params = dic_of_params

    def update_cleaner_params(self, dic_of_params):
        cleaner_params_ = self._cleaner_params # Current
        self.cleaner_params = dic_of_params # Dont catch this, checks and processes updates
        cleaner_params_.update(self._cleaner_params) # Now old with new updated ontop
        self._cleaner_params = cleaner_params_

    def pop_cleaner_param(self, key):
        self._cleaner_params.pop(key)
        if key in self._cleaners:
            warn('Cleaner itself has not been removed, only its params')

    @property
    def eventextractor(self):
        return self._eventextractor

    @eventextractor.setter
    def eventextractor(self, extractor):
        if extractor is not None and extractor not in EVENTEXTRACTORS:
            raise KeyError(f'Invalid event extractor: {extractor}')
        self._eventextractor = extractor

    @property
    def eventextractor_params(self):
        return self._eventextractor_params.copy() # shallow is intended

    @eventextractor_params.setter
    def eventextractor_params(self, dic_of_params):
        if not isinstance(dic_of_params, dict):
            raise ValueError(f'Not a dict: {dic_of_params}')

        dic_of_params = dic_of_params.copy()

        for extractor, params in dic_of_params.items():
            if extractor not in EVENTEXTRACTORS:
                raise KeyError(f'Invalid event extractor: {extractor}')
            if extractor != self.eventextractor:
                warn(f'Event extractor is not selected: {extractor}')

            params = EVENTEXTRACTORS[extractor].Params(params) # Dont catch this

            dic_of_params[extractor] = params

        self._eventextractor_params = dic_of_params

    def update_eventextractor_params(self, dic_of_params):
        eventextractor_params_ = self._eventextractor_params # Current
        self.eventextractor_params = dic_of_params # Dont catch this, checks and processes updates
        eventextractor_params_.update(self._eventextractor_params) # Now old with new updated ontop
        self._eventextractor_params = eventextractor_params_

    def pop_eventextractor_param(self, key):
        self._eventextractor_params.pop(key)
        if key == self.eventextractor:
            warn('Event extractor itself not automatically deselected')

    def to_dict(self):
        dic = {
            'trace_info': self.trace_info.to_dict(),
            'cleaners': self.cleaners,
            'cleaner_params': {
                cleaner: params.to_dict() for cleaner, params in self.cleaner_params.items()
                },
            'eventextractor': self.eventextractor,
            'eventextractor_params': {
                extractor: params.to_dict() for extractor, params in self.eventextractor_params.items()
                }
            }
        return dic

    def check_cleaner_settings(self):
        for cleaner in self._cleaners:
            if cleaner not in self._cleaner_params.keys():
                raise ValueError(f'Params for cleaner missing: {cleaner}')
            self._cleaner_params[cleaner].check_valid()
        for cleaner in self._cleaner_params.keys():
            if cleaner not in self._cleaners:
                warn(f'Params for cleaner present but cleaner not used: {cleaner}')
        for i in range(len(self._cleaners)):
            if 'filter' in self._cleaners[i] and i != 0:
                warn(f'Filters should go before other cleaners as filtering on nan containing data will result in large portions of data being nan-ed')

    def check_eventextractor_settings(self):
        if self.eventextractor is None:
            raise ValueError(f'No event extractor chosen')
        if self.eventextractor not in self._eventextractor_params.keys():
            raise ValueError(f'Params for chosen event extractor missing: {self.eventextractor}')
        self._eventextractor_params[self.eventextractor].check_valid()

        for extractor in self._eventextractor_params.keys():
            if extractor != self.eventextractor:
                warn(f'Params for not-selected event extractor present: {extractor}')

    def check_valid(self):
        if self.trace_info is not None:
            self.trace_info.check_valid()
        self.check_cleaner_settings()
        self.check_eventextractor_settings()
