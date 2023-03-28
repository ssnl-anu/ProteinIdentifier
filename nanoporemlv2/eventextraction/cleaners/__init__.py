#

__all__ = [
    'common',
    'filters',
    'zapmasker', 'trimmer', 'manualmasker'
    ]

from .zapmasker import ZapMasker
from .trimmer import Trimmer
from .manualmasker import ManualMasker
from .filters import PresetFilter, LowPassFilter

CLEANERS = [PresetFilter, LowPassFilter, ZapMasker, Trimmer, ManualMasker]
CLEANERS = {cleaner.name: cleaner for cleaner in CLEANERS}

# for cleaner in CLEANERS.keys():
#     assert cleaner in __all__
