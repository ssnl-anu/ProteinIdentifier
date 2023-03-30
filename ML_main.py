# -*- coding: utf-8 -*-

import time

import numpy as np
import scipy.signal as sig
import scipy.stats as stats

import matplotlib.pyplot as plt

from nanoporemlv2.featureeng.datasetio import load_dataset, scan_for_datasets, load_separated_by_meta
from nanoporemlv2.mltools.datasettools import *

from sklearn.model_selection import train_test_split ### ONLY USE AS train_VAL_split
from sklearn.model_selection import cross_val_score

from sklearn.model_selection import GridSearchCV
from sklearn.model_selection import StratifiedKFold

from sklearn.ensemble import RandomForestClassifier

from sklearn.cluster import KMeans

from sklearn.metrics import confusion_matrix, ConfusionMatrixDisplay
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from sklearn.metrics import make_scorer
from sklearn.metrics import confusion_matrix

from itertools import combinations
import pprint

#%%

logfilename = f'LOG FILE ADDRESS HERE'

logfile = open(logfilename, 'x')

def _print(*objects, sep=' ', end='\n'):
    print(*objects, sep=sep, end=end, file=logfile, flush=True)
    print(*objects, sep=sep, end=end)

LABEL_ORDER = ['BSA', 'ConA', 'BovineHb', 'HSA']

def multilinetabprint(obj, tabs=0):
    formatted = pprint.pformat(obj)
    for line in formatted.split('\n'):
        _print('\t'*tabs+line)
            
multilinetabprint0 = multilinetabprint
multilinetabprint1 = lambda obj: multilinetabprint(obj, tabs=1)
multilinetabprint2 = lambda obj: multilinetabprint(obj, tabs=2)
multilinetabprint3 = lambda obj: multilinetabprint(obj, tabs=3)

def tabprint(*objects, tabs=0):
    _print('\t'*tabs,end='')
    _print(*objects)

tabprint0 = tabprint
tabprint1 = lambda *objects: tabprint(*objects, tabs=1)
tabprint2 = lambda *objects: tabprint(*objects, tabs=2)
tabprint3 = lambda *objects: tabprint(*objects, tabs=3)

files = scan_for_datasets(r'PATH') #Insert Path of Files Here!

separated = load_separated_by_meta('signed_voltage', *files)

for volt in [0.5]:
    
    tabprint0('Voltage:', volt, tabs=0)
    datasets = separated[volt]
    
    combined = combine_datasets(*datasets)
    combined = nan_rows_removed(*combined)

    _, _y = combined
    labels = np.unique(_y)
    
    grouped = group_by_label(combined)
    counts = summarize_grouped(grouped)
    tabprint1('Total valid vectors:', counts)
    
    combis = []
    combis += list(combinations(labels, 2))
    #combis += list(combinations(labels, 3))
    #combis += list(combinations(labels, 4))
    
    for combi in combis:
        
        tabprint1('Combination:', combi)
        selgrouped = { key:val for key, val in grouped.items() if key in combi }
        
        equalrep = get_equal_rep_groups(selgrouped, sampling='random')
        repcount = len(equalrep[combi[0]][1])
        tabprint2("First how many vectors of each label used is:", repcount)
        
        testpct = 0.1
        tabprint2('Portion of each label in reduced set reserved for testing:', testpct)
        testsize = int(repcount*testpct//1)
        tabprint2('Vectors from end of each label in reduced set reserved for testing:', testsize)
        trainvalsize = repcount-testsize
        tabprint2('Num remaining vectors per label in reduced set for trainval:', trainvalsize)

        test_X, test_y = combine_datasets(
            *list( slice_dataset(*dataset, -testsize, None, None) for dataset in equalrep.values() )
            )
        trainval_X, trainval_y = combine_datasets(
            *list( slice_dataset(*dataset, None, trainvalsize, None) for dataset in equalrep.values() )
            )
        
        testscores = []
        confmats = []
        for repeati in range(10):
            tabprint2('Repeat #:', repeati)
            seed = time.time_ns() // 100 % 1_000_000_000
            rng = np.random.RandomState(seed)
            tabprint3('RNG for this repeat:', f'RandomState({seed})')
            rf = RandomForestClassifier(
                criterion='entropy',
                max_features='sqrt',
                class_weight='balanced'
                )
            param_grid = { # Only do search for main params
                "n_estimators": [80, 90, 100, 110, 120],
                "max_features": [0.3, "sqrt", None]
                }
            clf = GridSearchCV(
                rf, param_grid,
                cv=StratifiedKFold(n_splits=5, shuffle=False), 
                scoring=make_scorer(f1_score, average='weighted')
                )
            clf.fit(trainval_X, trainval_y)
            tabprint3('- CV results -')
            multilinetabprint3(clf.cv_results_)
            tabprint3('- Val F1-score of best model -')
            tabprint3(clf.best_score_)
            tabprint3('- Params of best model -')
            multilinetabprint3(clf.best_params_)
            testscore = clf.score(test_X, test_y)
            tabprint3('Test F1-score of best model:', testscore)
            confmat = confusion_matrix(
                test_y, clf.predict(test_X), 
                labels=[label for label in LABEL_ORDER if label in combi] # Match order in LABEL_ORDER
                )
            tabprint3('- Conf matrix from test of best model -')
            multilinetabprint3(confmat)
            testscores.append(testscore)
            confmats.append(confmat)
        
        tabprint2('- Test scores from repeats -')
        tabprint2(testscores)
        bestrepeati, highesttestscore = max(enumerate(testscores))
        lowesttestscore = min(testscores)
        avgtestscore = np.average(testscores)
        testscoresstd = np.std(testscores)
        tabprint2('Highest test score:', highesttestscore)
        tabprint2('Lowest test score:', lowesttestscore)
        tabprint2('Average test score:', avgtestscore)
        tabprint2('Test scores std:', testscoresstd)
        tabprint2('- Conf mat from repeat with highest test score -')
        multilinetabprint2(confmats[bestrepeati])
        
        
