# -*- coding: utf-8 -*-

from warnings import warn

import numpy as np

import matplotlib.pyplot as plt
from matplotlib.widgets import Slider, TextBox, Button

from ..utils.validators import check_positive

class ScrollableFig:

    def __init__(self, view_size=100_000):
        plt.ion()

        self._view_size = view_size

        self._fig, self._ax = plt.subplots()
        # adjust the main plot to make room for widgets
        self._fig.subplots_adjust(bottom=0.25)
        self._init_widget_axes()
        self._fig.sca(self.ax)

        self._view_start = 0
        self._view_end = self._view_size
        self._line_update_funcs = []
        self._lines = {}

        self._init_view_slider()
        self._init_set_view_textbox()
        self._init_size_slider()
        self._init_enable_autoscaley_button()

    def _init_widget_axes(self):
        self._view_slider_ax = self._fig.add_axes([0.175, 0.125, 0.65, 0.03])
        self._set_view_textbox_ax = self._fig.add_axes([0.825, 0.04, 0.15, 0.05])
        self._enable_autoscaley_button_ax = self._fig.add_axes([0.45, 0.04, 0.275, 0.05])
        self._size_slider_ax = self._fig.add_axes([0.125, 0.045, 0.2, 0.03])

    def _init_view_slider(self):

        self._view_slider = Slider(
            ax=self._view_slider_ax,
            label='View',
            valmin=self._view_size,
            valmax=self._view_size+1e-9, # +1e-9 as valmin same as valmax not allowed
            valinit=self._view_size,
            orientation='horizontal',
            valfmt='%d\n/{}'.format(self._view_size),
            color='lightgrey' # Slider progress color
            # Slider progress color matches track color
            # This avoid giving the impression that the view is larger
            # The view is only shifting
            )
        self._view_slider.on_changed(self._view_slider_callback)

    def _view_slider_callback(self, val):
        self._view_end = int(val) # Guranteed to be >= self.view_size
        self._view_start = self._view_end - self._view_size # >= 0
        # Enable x axis autoscale if disabled
        self._ax.set_autoscalex_on(True)
        self._update_lines()

    def _update_lines(self):
        view_start = self._view_start
        view_end = self._view_end
        for line_update_func in self._line_update_funcs:
            line_update_func(view_start, view_end)

        # recompute the ax.dataLim
        self._ax.relim()

        self._redraw()

    def _redraw(self):
        # update ax.viewLim using the new dataLim
        self._ax.autoscale_view()
        # Redraw the figure to ensure it updates
        self._fig.canvas.draw_idle()

    def _init_set_view_textbox(self):
        self._set_view_textbox = TextBox(
            ax=self._set_view_textbox_ax,
            label='Jump: ',
            initial=''
            )
        self._set_view_textbox.on_submit(self._set_view_textbox_callback)

    def _set_view_textbox_callback(self, text):
        try:
            view_end = int(text)
        except ValueError:
            self._set_view_textbox.eventson = False
            self._set_view_textbox.set_val('')
            self._set_view_textbox.eventson = True
            return

        valmax = self._view_slider.valmax
        valmin = self._view_size

        if view_end > valmax:
            view_end = valmax

        elif view_end < self._view_size:
            view_end = self._view_size

        self._set_view_textbox.eventson = False
        self._set_view_textbox.set_val(view_end)
        self._set_view_textbox.eventson = True

        self._view_slider.set_val(view_end) # Sync slider and also do all updating

    def _init_size_slider(self):
        self._size_slider = Slider(
            ax=self._size_slider_ax,
            label='Size ',
            valmin=1000,
            valmax=1_000_000,
            valinit=self._view_size,
            valstep=250,
            orientation='horizontal',
            valfmt=' %d'
            )
        self._size_slider.on_changed(self._size_slider_callback)

    def _size_slider_callback(self, val):
        view_size = int(val)
        self._update_view_size(view_size)

    def _update_view_size(self, view_size):
        self._view_size = view_size

        self._update_view_slider_valmin(view_size)

        if self._view_slider.valmax <= view_size:
            self._update_view_slider_valmax(view_size+1e-6)

        if self._get_view_slider_val() < view_size:
            self._view_slider.set_val(view_size)
        else:
            self._view_start = self._view_end - view_size
            self._update_lines()


    def _update_view_slider_valmin(self, valmin):
        self._view_slider.valmin = valmin
        self._view_slider_ax.set_xlim(left=valmin)
        # Update the red line's position
        self._view_slider_ax.get_lines()[0].set_xdata([valmin, valmin])

    def _update_view_slider_valmax(self, valmax):
        self._view_slider.valmax = valmax
        self._view_slider_ax.set_xlim(right=valmax)
        self._view_slider.valfmt = '%d\n/{}'.format(int(valmax))
        self._view_slider.set_val(self._view_end) # Set val to current val to update displayed valmax

    def _get_view_slider_val(self):
        return self._view_slider_ax.get_lines()[1].get_xdata()[0]

    def _init_enable_autoscaley_button(self):
        self._enable_autoscaley_button = Button(
            ax=self._enable_autoscaley_button_ax,
            label='(Re)enable autoscale y'
            )
        self._enable_autoscaley_button.on_clicked(self._enable_autoscaley_button_callback)

    def _enable_autoscaley_button_callback(self, _):
        self._ax.set_autoscaley_on(True)
        self._redraw()

    def plot(self, *args, **kwargs):
        argc = len(args)
        if argc == 0:
            raise ValueError('y not specified')
        if argc > 3:
            raise NotImplementedError('Signatures with >3 args not implemented')

        x = None
        y = None
        fmt = None

        if argc == 1:
            y = args[0]

        if argc == 2:
            if isinstance(args[1], str):
                fmt = args[1]
                y = args[0]
            else:
                y = args[1]
                x = args[0]

        if argc == 3:
            fmt = args[2]
            y = args[1]
            x = args[0]

        if x is None:
            x = np.arange(len(y))

        call_args_ = [
            x[self._view_start:self._view_end],
            y[self._view_start:self._view_end],
            fmt if fmt is not None else None
            ]
        call_args = [arg for arg in call_args_ if arg is not None]

        line, = self._ax.plot(
            *call_args,
            **kwargs
            )

        length = len(y)
        if length > self._view_slider.valmax:
            self._update_view_slider_valmax(length)

        def line_update_func(view_start, view_end):
            line.set_xdata( x[view_start:view_end] )
            line.set_ydata( y[view_start:view_end] )

        self._line_update_funcs.append(line_update_func)
        self._lines[line_update_func] = line

        self._update_lines()

        if self.ax.legend_ is not None:
            plt.legend(loc='upper right')

    def remove_last_line(self):
        line_update_func = self._line_update_funcs.pop()
        line = self._lines[line_update_func]
        del self._lines[line_update_func]
        del line_update_func
        # self._ax.lines.remove(line)
        line.remove()
        del line
        if self.ax.legend_ is not None:
            plt.legend(loc='upper right')

    def close(self):
        plt.close(self._fig)

    def activate(self):
        plt.figure(self._fig)

    @property
    def fig(self):
        return self._fig

    @property
    def ax(self):
        '''
        main ax
        '''
        return self._ax

    @property
    def view_size(self):
        return self._view_size

    @view_size.setter
    def view_size(self, value):
        value = int(value)
        check_positive(value)
        if value < self._size_slider.valmin:
            value = self._size_slider.valmin
        self._size_slider.eventson = False
        self._size_slider.set_val(value)
        self._size_slider.eventson = True
        self._update_view_size(value)

    @property
    def view_start(self):
        return self._view_start

    @view_start.setter
    def view_start(self, value):
        value = int(value)
        check_positive(value)
        self._view_slider.set_val(value + self._view_size)

    @property
    def view_end(self):
        return self._view_end

    @view_end.setter
    def view_end(self, value):
        value = int(value)
        check_positive(value)
        if value < self._view_size:
            value = self._view_size
        self._view_slider.set_val(value)

    def sync_view(self, other_sfig):
        self.view_end = other_sfig.view_end
        self.view_size = other_sfig.view_size

    def update_lines(self):
        self._update_lines()
