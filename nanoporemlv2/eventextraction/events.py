# -*- coding: utf-8 -*-

from warnings import warn

from collections import UserList
from pathlib import Path
from zipfile import ZipFile
import json

import numpy as np

from ..utils import npztools

from ..dataloaders.common import Trace, Info

from .event import Event, PortableEvent

from ..signal.signal import Signals

#%%

class Events(UserList):
    def __init__(self, events):
        for event in events:
            if not isinstance(event, Event):
                raise ValueError(f'Not an Event object: {event}')
        self.data = events
        self._loaded_from = None
        self._loaded_trace_info = None
        self._loaded_meta = None
        self._extracted_from = None

    @property
    def events(self):
        return self.data


    def filtered(self, *filters):
        good = Events([])
        for event in self.events:
            for filt in filters:
                if filt(event) == True:
                    good.append(event)
        good._loaded_from = self._loaded_from
        good._extracted_from = self._extracted_from
        return good


    @classmethod
    def init_from_extractor(cls, extractor):
        events = []
        trace = extractor.trace
        baseline = extractor.baseline
        for start, end in extractor.raw_events:
            event = Event(trace, baseline, start, end)
            events.append(event)
        events = Events(events)
        events._extracted_from = extractor
        return events

    @classmethod
    def init_from_pipeline(cls, pipeline):
        events = cls.init_from_extractor(pipeline.extractor)
        events._extracted_from = pipeline
        return events

    @property
    def trace_info(self):
        if self.loaded_from is not None:
            return self._loaded_trace_info
        elif self.extracted_from is not None:
            return self.extracted_from.trace.info
        else:
            return self.events[0].trace_info

    def check_consistent(self):
        ref_trace_info_dic = self.trace_info.to_dict()
        for event in self.events:
            if event.trace_info.to_dict() != ref_trace_info_dic:
                raise ValueError(f'Inconsistent event: {event}')

    @property
    def loaded_from(self):
        return self._loaded_from

    @property
    def loaded_meta(self):
        return self._loaded_meta

    @property
    def extracted_from(self):
        return self._extracted_from

    def meta_dict(self):
        '''
        On first save:

            Want source_file to be the trace's source
            If extracted via pipeline:
                Want extracted_from to say "pipeline"
                Want to include pipeline settings
            If not extracted via pipeline but manual by extractor:
                Want extracted_from to say extractor name
                Want to include extractor params

        On second save:
            Want source_file to be the original events file
            Want to keep copy of original source_file, which is trace source, and also keep copy of extraction info
                This is just all of original events file's meta

        On subsequent saves:
            Want source_file to be the previous events file
            Want to carry the meta of original events file
                Do not want to make a copy of previous events file's meta, since the source of that is not trace source

        '''
        dic = {}

        assert not ( (self.loaded_from is not None) and (self.extracted_from is not None) )

        if self.loaded_from is not None: # Not first save
            dic['source_file'] = str(self.loaded_from.absolute())
            loaded_meta = self.loaded_meta
            if 'original_meta' in loaded_meta:
                dic['original_meta'] = loaded_meta['original_meta']
            else:
                dic['original_meta'] = loaded_meta
        else: # First save
            try:
                dic['source_file'] = str(self.extracted_from.trace.raw.path)
            except Exception:
                dic['source_file'] = None

        if self.extracted_from is not None: # First save
            if hasattr(self.extracted_from, 'settings'): # Extracted via pipeline
                dic['extracted_from'] = 'pipeline'
                pipeline = self.extracted_from
                dic['settings'] = pipeline.settings.to_dict()
            elif hasattr(self.extracted_from, 'params'): # Extracted with extractor; Pipeline not used
                extractor = self.extracted_from
                dic['extracted_from'] = extractor.name
                dic['params'] = extractor.params.to_dict()
            else:
                dic['extracted_from'] = None

        return dic

    @staticmethod
    def save_(path, events, overwrite=False):
        # WARNING:
        #   MANUAL CHANGES WILL _NOT_ BE REFLECTED IN SAVED METADATA
        #   e.g.
        #       Manual trace edits
        #       Manual baseline changing post extractor run
        #       Manual add or removal of events
        #   This function will only check that the trace info is consistent

        path = Path(path)

        if path.suffixes[-2:] != ['.events', '.npz']:
            path = path.with_suffix(path.suffix + '.events.npz')

        meta = events.meta_dict()

        events.check_consistent()

        portable_events = []
        for event in events:
            if not isinstance(event, PortableEvent):
                portable_event = event.to_portable()
            else:
                portable_event = event
            portable_events.append(portable_event)

        mode = 'xb'
        if overwrite:
            mode = 'wb'

        arrs = []
        bounds = ''
        for portable_event in portable_events:
            arr = np.array([
                portable_event.current,
                portable_event.time,
                portable_event.baseline
                ])
            arrs.append(arr)
            bounds += f'{portable_event.start},{portable_event.end},{portable_event.orig_start},{portable_event.orig_end}\n'

        with open(path, mode) as f:
            np.savez_compressed(f, *arrs)

        with ZipFile(path, 'a') as zf:
            zf.writestr(
                'trace_info.json',
                events.trace_info.to_json()
                )
            zf.writestr(
                'bounds.csv',
                bounds
                )
            zf.writestr(
                'meta.json',
                json.dumps(meta, indent=2)
                )

    def save(self, path, overwrite=False):
        self.__class__.save_(path, self, overwrite=overwrite)

    @classmethod
    def load(cls, path):
        path = Path(path)

        npzf = np.load(path)

        meta = json.loads(npzf['meta.json'])

        trace_info = Info.from_json(npzf['trace_info.json'])
        try:
            trace_info.check_valid()
        except Exception:
            warn('Trace info not (fully) valid')

        bounds = [
            [int(row[i]) for i in range(4)] \
            for row in npztools.csv_reader_bstr(npzf['bounds.csv'])
            ]

        arr_names = npztools.get_arr_filenames(npzf)

        n_arrs = len(arr_names)
        n_bounds = len(bounds)
        if n_arrs != n_bounds:
            raise ValueError('Arrays and bounds mismatch: {n_arrs}, {n_bounds}')

        events = []
        for i in range(n_bounds):

            arr = npzf[arr_names[i]]
            current = arr[0,:]
            time = arr[1,:]
            baseline = arr[2,:]

            rel_start, rel_end, orig_start, orig_end = bounds[i]

            event = PortableEvent(
                trace_info,
                current,
                time,
                baseline,
                rel_start,
                rel_end,
                orig_start,
                orig_end
                )

            events.append(event)

        events = cls(events)
        events._loaded_from = path
        events._loaded_meta = meta
        events._loaded_trace_info = trace_info

        return events

    @staticmethod
    def scan(path, recursive=True):
        scan_dir = Path(path)

        if recursive:
            glob_pattern = '**/*.events.npz'
        else:
            glob_pattern = '*.events.npz'

        return list(scan_dir.glob(glob_pattern))

    def to_signals(self):
        signals = []
        for event in self.events:
            signal = event.to_signal()
            if signal.has_nan():
                continue
            ##
            bl = event.view_baseline()
            diff = max(bl) - min(bl)
            if abs(diff) > 0.05:
                continue
            ##
            signals.append(signal)
        signals = Signals(signals)
        signals._extracted_from = self
        return signals
