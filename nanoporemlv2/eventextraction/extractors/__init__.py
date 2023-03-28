#

__all__ = [
    'common',
    'ftrtextractor'
    ]

from .ftrtextractor import FTRTExtractor

EVENTEXTRACTORS = [FTRTExtractor]
EVENTEXTRACTORS = {extractor.name: extractor for extractor in EVENTEXTRACTORS}

from ...interactiveutils.input_funcs import make_input_opt

input_eventextractor = make_input_opt(EVENTEXTRACTORS)

for eventextractor in EVENTEXTRACTORS.keys():
    assert eventextractor in __all__
