# -*- coding: utf-8 -*-

def get_arr_filenames(npzf):
    arr_filenames = []
    for filename in npzf.files:
        if filename[:4] == 'arr_':
            arr_filenames.append(filename)
    return arr_filenames

from zipfile import ZipFile
def writestr(npz_path, filename, string):
    if filename[:-4] == '.npy' or filename[:4] == 'arr_':
        raise ValueError('Illegal filename - cannot start with "arr_" or end with ".npy"')
    with ZipFile(npz_path, 'a') as zf:
        zf.writestr(filename, string)

def readstr(npzf, filename):
    return npzf[filename].decode()

def csv_reader_bstr(bstr):
    for row in bstr.decode().strip().split('\n'):
        yield row.split(',')

def gen_csv_str(table):
    csv_str = ''
    for row in table:
        csv_str += ','.join([str(ele) for ele in row])
        csv_str += '\n'
    return csv_str
