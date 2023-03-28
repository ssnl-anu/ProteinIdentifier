# -*- coding: utf-8 -*-

import asyncio

def check_no_running_event_loop():
    running_loop = None
    try:
        running_loop = asyncio.get_running_loop()
    except RuntimeError:
        pass # No running loop
    return running_loop is None

def run_async(func):
    async def async_func(*args, **kwargs):
        return func(*args, **kwargs)

    def wrapper(*args, **kwargs):
        if check_no_running_event_loop == False:
            raise RuntimeError('Existing running asyncio event loop detected. Inputs will not work. Please rerun in an external (non-IDE) console')
        return asyncio.run(async_func(*args, **kwargs))

    return wrapper

# Matplotlib plots do not draw properly if they are immediately followed by a normal input
# Running inputs async avoids this problem
# This makes the inputs not work in IDEs where the IDE console already uses an event loop though
# There is no issues when ran in a standard terminal (assuming all the required libraries are installed)

@run_async
def input_1(prompt=''):
    while True:
        resp = input(prompt+' [1=Y,Enter=N] > ')
        if resp in ('1', ''):
            break
    return resp == '1'

def input_1_default(prompt='', default=None):
    assert default is None or isinstance(default, bool)
    while True:
        resp = input(prompt+' [1=Y,0=N]{} >'.format(
            '[Enter={}]'.format(default) if default is not None else '')
            )
        if default is not None and resp == '':
            resp = str(int(default))
        if resp in ('1', '0'):
            break
    return resp == '1'

def input_str_default(prompt='', default=None):
    while True:
        resp = input(prompt+' {}>'.format(
            '[Enter={}] '.format(default) if default is not None else '')
            )
        if default is not None and resp == '':
            resp = default
        if resp != '':
            break
    return resp

@run_async
def input_1_safe(prompt=''):
    while True:
        resp = input(prompt+' [1=Y,0=N] > ')
        if resp in ('1', '0'):
            break
    return resp == '1'

@run_async
def input_int_strict(prompt='', pos_only=False, zero_ok=False, default=None):
    if default is not None:
        assert type(default) == int
        if zero_ok and default == 0:
            pass
        elif pos_only:
            assert default > 0
    while True:
        resp = input(prompt+'{} > '.format(
            ' [Enter={}]'.format(default) if default is not None else ''
            ))
        if '.' in resp:
            continue
        if default is not None and resp == '':
            resp = default
        try:
            num = int(resp)
        except ValueError:
            continue
        if pos_only and num < 0:
            continue
        if (not zero_ok) and num == 0:
            continue
        return num

@run_async
def input_float(prompt='', pos_only=False, neg_only=False, default=None):
    assert not (pos_only and neg_only)
    if default is not None:
        assert type(default) == float
        if pos_only:
            assert default > 0
        if neg_only:
            assert default < 0
    while True:
        resp = input(prompt+'{} > '.format(
            ' [Enter={}]'.format(default) if default is not None else ''
            ))
        if default is not None and resp == '':
            resp = default
        try:
            num = float(resp)
        except ValueError:
            continue
        if pos_only and num <= 0:
            continue
        if neg_only and num >= 0:
            continue
        return num


def make_input_opt(opts):
    opts = tuple(opts)
    tip = '[' + ', '.join('{}={}'.format(i, opt) for i, opt in enumerate(opts)) + ']'
    def input_opt(prompt='', default=None):
        if default is not None:
            assert default in opts
        while True:
            resp = input(prompt+'\n'+
                         tip + '{}'.format('[Enter={}]'.format(default) if default is not None else '') +' > ')
            if default is not None and resp == '':
                resp = opts.index(default)
            try:
                i = int(resp)
            except ValueError:
                continue
            if i < 0 or i >= len(opts):
                continue
            return opts[i]
    return input_opt
