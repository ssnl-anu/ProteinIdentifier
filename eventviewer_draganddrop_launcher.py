# -*- coding: utf-8 -*-

import sys

from nanoporemlv2.eventextraction.events import Events
from nanoporemlv2.eventextraction.eventviewer import EventViewer

# Drag and drop only works if your anaconda python is the default python!
# Add shebang otherwise if you want to make it work
# Alternatively just use this as a commandline tool

if __name__ == '__main__':
    events_file = sys.argv[1]
    events = Events.load(events_file)
    EventViewer(events)
    input('Press Enter to quit')
