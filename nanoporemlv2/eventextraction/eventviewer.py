# -*- coding: utf-8 -*-

import tkinter as tk

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
import matplotlib.pyplot as plt

#%%

class EventViewer:
    def __init__(self, events):

        self.events = events # Setter also inits key vars

        self._root = tk.Tk()
        self._root.wm_title('Event viewer')


        self._init_canvas()
        self._init_toolbar()
        self._init_ilabel()
        self._init_navbuttons()
        self._init_jumptool()
        self._pack_root()
        self._init_line()

        print('Starting event viewer... Close event viewer window when done viewing to unblock interpreter.')
        tk.mainloop()

    def _init_canvas(self):
        self._fig = Figure()
        self._ax = self._fig.add_subplot()
        self._canvas = FigureCanvasTkAgg(self._fig, master=self._root)

    def _init_toolbar(self):
        self._toolbar = NavigationToolbar2Tk(self._canvas, self._root, pack_toolbar=False)

    def _init_ilabel(self):
        self._ilabel = tk.Label(master=self._root, text=self._ilabel_fstr.format(self._i))

    def _init_navbuttons(self):
        self._navbuttons = tk.Frame()
        self._forwardbutton = tk.Button(master=self._navbuttons, text='Next event', command=self.forward)
        self._backwardbutton = tk.Button(master=self._navbuttons, text='Previous event', command=self.backward)

        self._forwardbutton.pack(side=tk.RIGHT)
        self._backwardbutton.pack(side=tk.LEFT)

    def _init_jumptool(self):
        self._jumptool = tk.Frame()
        self._ientry = tk.Entry(master=self._jumptool)

        def jumpbutton_callback():
            new_i = self._ientry.get()
            try:
                self.i = new_i
            except IndexError:
                self._ientry.select_range(0, tk.END)

        self._jumpbutton = tk.Button(master=self._jumptool, text='Jump', command=jumpbutton_callback)
        self._ientry.pack(side=tk.LEFT)
        self._jumpbutton.pack(side=tk.RIGHT)

    def _pack_root(self):
        self._jumptool.pack(side=tk.BOTTOM)
        self._navbuttons.pack(side=tk.BOTTOM)
        self._ilabel.pack(side=tk.BOTTOM)
        self._toolbar.pack(side=tk.BOTTOM, fill=tk.X)
        self._canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)

    def _init_line(self):
        self._plot_event(0)

    @property
    def events(self):
        return self._events

    @events.setter
    def events(self, seq):
        if len(seq) == 0:
            raise ValueError('No events')
        self._events = seq
        self._i = 0
        self._ilabel_fstr = 'Event index: ' + '{}' + f'/{len(seq)-1}'

    @property
    def i(self):
        return self._i

    @i.setter
    def i(self, val):
        new_i = int(val)
        if new_i < 0 or new_i >= len(self._events):
            raise IndexError('Index out of range')
        self._switch_event(new_i)

    def forward(self):
        next_i = self._i + 1
        if next_i >= len(self._events):
            return
        self._switch_event(next_i)

    def backward(self):
        prev_i = self._i -1
        if prev_i < 0:
            return
        self._switch_event(prev_i)

    def _switch_event(self, i):
        self._clear()
        self._i = i
        self._ilabel['text'] = self._ilabel_fstr.format(i)
        self._plot_event(i)

    def _plot_event(self, i):
        event = self._events[i]
        # self._line, = self._ax.plot(event[0], event[1])
        event.show(expand=len(event), ax=self._ax)
        self._ax.set_autoscalex_on(True)
        self._ax.set_autoscaley_on(True)
        self._ax.relim()
        self._ax.autoscale_view()
        self._canvas.draw_idle()
        self._toolbar.update()

    def _clear(self):
        # if self._line is None:
        #     return
        # self._line.remove()
        # self._line = None

        self._ax.lines.clear()
        self._ax.lines # Trigger GC check
        self._ax.collections.clear()
        self._ax.collections
        # Note GC may not run even when triggered
        # Due to low amount of total garbage
        # (Since event plots are not big in size)
