# -*- coding: utf-8 -*-

import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt

from nanoporemlv2.featureeng.datasetio import load_dataset, scan_for_datasets, load_separated_by_meta
from nanoporemlv2.mltools.datasettools import *

from sklearn.cluster import KMeans
import scipy.stats as stats

from pathlib import Path

import time

import scipy.signal as sig
import scipy.stats as stats

from sklearn.model_selection import train_test_split ### ONLY USE AS train_VAL_split
from sklearn.model_selection import cross_val_score

from sklearn.model_selection import GridSearchCV
from sklearn.model_selection import StratifiedKFold

from sklearn.ensemble import RandomForestClassifier

from sklearn.metrics import confusion_matrix, ConfusionMatrixDisplay
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from sklearn.metrics import make_scorer
from sklearn.metrics import confusion_matrix

from itertools import combinations
import pprint

#%%
import os
os.environ["MKL_NUM_THREADS"]="14"
os.environ["NUMEXPR_NUM_THREADS"]="14"
os.environ["OMP_NUM_THREADS"]="14"

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
multilinetabprint4 = lambda obj: multilinetabprint(obj, tabs=4)

def tabprint(*objects, tabs=0):
    _print('\t'*tabs,end='')
    _print(*objects)

tabprint0 = tabprint
tabprint1 = lambda *objects: tabprint(*objects, tabs=1)
tabprint2 = lambda *objects: tabprint(*objects, tabs=2)
tabprint3 = lambda *objects: tabprint(*objects, tabs=3)
tabprint4 = lambda *objects: tabprint(*objects, tabs=4)

freq = '100k'
#freq = '40M'

def get_fullres_ml_cols(X):
    if freq == '100k':
        X_fullres = X[:, :200]
        X_ml = X[:, 200:]
    elif freq == '40M':
        X_fullres = X[:, :20_000]
        X_ml = X[:, 20_000:]
    else:
        assert False
    return X_fullres, X_ml
    
if freq == '100k':
    scanroot = Path(r'ENTER PATH HERE') # 100ksps
elif freq == '40M':
    scanroot = Path(r"ENTER PATH HERE")
else:
    assert False

files = scan_for_datasets(scanroot)


COL_MAP = { # For the ML part (avg10pSSpGeoPlus) of the vector
    'height': 0, # Height of highest peak/valley, in units of standardization. Height/highest is relative to baseline
    'fwhm': 1, # FW@HM in seconds. Height is relative to baseline, max is height of highest peak/valley as per height
    'heightatfwhm': 2, # Half max height in units of standardization. Definitions as before for height, max and hm
    'area': 3, #Sum (sample period * standardized value for values in event), this is units of standardisation * seconds
    'basewidth': 4, # Full width at base in seconds, as per event acquisition
    'skew': 5, # Skew of signal (standardization units and seconds)
    'kurt': 6, # Kurtosis of signal (standardization units and seconds)
    }

def get_main_cluster(dataset):
    dataset = nan_rows_removed(*dataset)
    X, y = dataset
    X_fullres, X_ml = get_fullres_ml_cols(X)
    
    ## Min Max Filtering 
    # ind = np.logical_and(
    #     X_fullres[:, COL_MAP['basewidth']] < 0.5e-3,
    #     X_fullres[:, COL_MAP['basewidth']] > 0.1e-3,
    #     # X_fullres[:, COL_MAP['height']] > 30
    #     )
    # dataset = dataset[0][ind, :], dataset[1][ind]
    # X, y = dataset
    # X_fullres, X_ml = get_fullres_ml_cols(X)
    
    ## Transformations    
    X_fullres = expand_and_center(X_fullres)

    ## Select clustering target
    X_clustering = X_fullres
    # X_clustering = np.concatenate( (X_fullres, X_ml), axis=1)
    
    ## RNG
    seed = time.time_ns() // 100 % 1_000_000_000
    # seed = 0
    rng = np.random.RandomState(seed)
    # rng = seed
    if type(rng) == int:
        tabprint3(f'RNG: {seed}')
    else:
        tabprint3(f'RNG: RandomState({seed})')
        
    ## Init
    n_clusters = 4 # Starting n_clusters
    last_max_pcorr = 0.0 # Do not edit
    while n_clusters >= 4: # Min n_clusters
        tabprint3('Clusters:', n_clusters)
        
        ## Do clustering
        kmeans = KMeans(n_clusters=n_clusters, random_state=rng).fit(X_clustering)
        kmeans.predict(X_clustering)
        cluster_centers = kmeans.cluster_centers_
        
        ## Stats
        ## Cluster sizes
        cluster_sizes = {}
        for i in range(len(cluster_centers)):
            cluster_size = np.count_nonzero(kmeans.labels_==i)
            cluster_sizes[i] = cluster_size
        sorted_clusters = sorted(cluster_sizes.keys(), key=lambda key: cluster_sizes[key], reverse=True)
        largest_cluster = sorted_clusters[0]
        tabprint4('Cluster sizes:', cluster_sizes)
        tabprint4('Largest cluster:', largest_cluster)
        
        ## Stats
        ## Pairwise similarities (pearson coeff) between each cluster centers
        tabprint4('- Pairwise similarities -')
        pcorrs = []
        for i in range(len(cluster_centers)):
            for j in range(len(cluster_centers)):
                if j> i:
                    pcorr = stats.pearsonr(cluster_centers[i], cluster_centers[j])[0]
                    pcorrs.append(pcorr)
                    tabprint4(i,j,pcorr)
        max_pcorr = max(pcorrs) if len(pcorrs) > 0 else 0.0 # Similarity value of the most similar pair of cluster centers
        tabprint4('Similarity of most similar pair:', max_pcorr)
        
        ## Termination condition
        delta_max_pcorr = last_max_pcorr - max_pcorr # max_pcorr from last n_cluster's iteration - max_pcorr from current n_cluster's iteration
        tabprint4('Change in max similarity:', delta_max_pcorr)
        # if max_pcorr < 0.85: # Stop when all cluster centers below centain similarity value
        #     break
        # if abs(delta_max_pcorr) < 0.1: # Stop when converge (as measured by small change in max_pcorr)
        #     break
        # if n_clusters <= 4 and max_pcorr < 0.85: # Additionally enforce a max n_cluster
        #     break
    
        ## Loop contiuation matters
        n_clusters -= 1
        last_max_pcorr = max_pcorr

    ## Select cluster to retrieve
    wanted_cluster_idx = 2 # Index of wanted cluster, 0 for largest cluster, 1 for next largest cluster, so on
    ## Retrieve selected cluster
    assert wanted_cluster_idx < n_clusters
    ind = kmeans.labels_ == sorted_clusters[wanted_cluster_idx] 
    ## Select feature set to return
    # X_retfrom = X_clustering
    X_retfrom = X_ml
    # X_retfrom = X_fullres
    ## Retrieve selected features of selected cluster
    X_ret, y_ret = (X_retfrom[ind,:], y[ind])

    ## Optionally select additional clusters
    n_extra_clusters_to_inc = 0 # How many extra (smaller) clusters to include
    ## Retrieve extra clusters and combine
    assert wanted_cluster_idx + n_extra_clusters_to_inc < n_clusters
    for i in range(n_extra_clusters_to_inc):
        ind_ = kmeans.labels_ == sorted_clusters[wanted_cluster_idx+1+i]
        # X_ret, y_ret = combine_datasets_Xy(X_ret, y_ret, X_clustering[ind_,:], y[ind_])
        X_ret, y_ret = combine_datasets_Xy(X_ret, y_ret, X_retfrom[ind_,:], y[ind_])

    return (X_ret, y_ret)    

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
    
    _combis = []
    #_combis += list(combinations(labels, 2))
    #_combis += list(combinations(labels, 3))
    _combis += list(combinations(labels, 4))    
    
    combis = []
    for _combi in _combis:
        combi = tuple([label for label in LABEL_ORDER if label in _combi])
        combis.append(combi)
    
    for combi in combis:
        
        tabprint1('Combination:', combi)
        selgrouped = { key:val for key, val in grouped.items() if key in combi }
        
        testpct = 0.2
        tabprint2('Portion of each label reserved for test set precursors:', testpct)
        
        testprecursors = {}
        trainvalprecursors = {}
        
        for label, dataset in selgrouped.items():
            totsize = counts[label]
            testprecursorsize = int(totsize*testpct//1)
            tabprint3(f"Vectors from end of {label}'s set reserved as test set precursor:", testprecursorsize)
            trainvalprecursorsize = totsize-testprecursorsize
            tabprint3(f"Num remaining vectors from {label}'s set remaining for trainval set precursor:", trainvalprecursorsize)
            testprecursors[label] = slice_dataset(*dataset, -testprecursorsize, None, None)
            trainvalprecursors[label] = slice_dataset(*dataset, None, trainvalprecursorsize, None)
        
        tabprint2('Run cluster for test precursors:')
        testsets = {}
        for label, testprecursor in testprecursors.items():
            tabprint3(f"- {label} -")
            testset = get_main_cluster(testprecursor)
            testsetsize = len(testset[1])
            tabprint3('Vectors in clustering output:', testsetsize)
            testsets[label] = testset
        
        testsets_equalrep = get_equal_rep_groups(testsets, sampling='random')
        actualtestsize = len(testsets_equalrep[combi[0]][1]) # per label
        tabprint2("First how many vectors of each label's test set used to construct full test set:", actualtestsize)
        test_X, test_y = combine_datasets(*testsets_equalrep.values())
        
        tabprint2('Run cluster for trainval precursors:')
        trainvalsets = {}
        for label, trainvalprecursor in trainvalprecursors.items():
            tabprint3(f"- {label} -")
            trainvalset = get_main_cluster(trainvalprecursor)
            trainvalsetsize = len(trainvalset[0])
            tabprint3('Vectors in clustering output:', trainvalsetsize)
            trainvalsets[label] = trainvalset
        
        trainvalsets_equalrep = get_equal_rep_groups(trainvalsets, sampling='sequential')
        actualtrainvalsize = len(trainvalsets_equalrep[combi[0]][1]) # per label
        tabprint2("First how many vectors of each label's trainval set used to construct full trainval set:", actualtrainvalsize)
        trainval_X, trainval_y = combine_datasets(*trainvalsets_equalrep.values())
            
        actualtestratio = actualtestsize/actualtrainvalsize
        tabprint2('Ratio of full test set to full trainval set:', actualtestratio)
        
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
        
        