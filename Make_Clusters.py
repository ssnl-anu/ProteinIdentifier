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

_print = print
def tabprint(*objects, tabs=0):
    _print('\t'*tabs,end='')
    _print(*objects)

tabprint0 = tabprint
tabprint1 = lambda *objects: tabprint(*objects, tabs=1)
tabprint2 = lambda *objects: tabprint(*objects, tabs=2)
tabprint3 = lambda *objects: tabprint(*objects, tabs=3)







import scienceplots
import matplotlib as mpl
plt.style.use(['science','nature','no-latex'])
plt.rcParams['font.family'] = 'DeJavu Serif'
plt.rcParams['font.serif'] = ['Helvetica']
csfont = {'fontname':'Comic Sans MS'}
hfont = {'fontname':'Helvetica'}
%matplotlib qt

import seaborn as sns
plt.rcParams.update({
      # specify font here
     "font.size":12.5})          # specify font size here
plt.rcParams.update({'figure.dpi': '200'})





#%%

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
    scanroot = Path(r'E:\PaperBlue\Dataset_35kHzFiltered_SqrtStd_FullRes200pAvg10pSSpGeoPlus_Real') # 100ksps
elif freq == '40M':
    scanroot = Path(r'E:\PaperRed\Dataset_100kHzFiltered_SqrtStd_FullRes20000pAvg10pSSpGeoPlus_Real') # 40Msps
else:
    assert False

#label = 'BSA' # S6
#label = 'HSA' # S7
#label = 'ConA' # S8
label = 'BovineHb' # S9

files = scan_for_datasets(scanroot/label)

COL_MAP = { # For the ML part (avg10pSSpGeoPlus) of the vector
    'height': 0, # Height of highest peak/valley, in units of standardization. Height/highest is relative to baseline
    'fwhm': 1, # FW@HM in seconds. Height is relative to baseline, max is height of highest peak/valley as per height
    'heightatfwhm': 2, # Half max height in units of standardization. Definitions as before for height, max and hm
    'area': 3, #Sum (sample period * standardized value for values in event), this is units of standardisation * seconds
    'basewidth': 4, # Full width at base in seconds, as per event acquisition
    'skew': 5, # Skew of signal (standardization units and seconds)
    'kurt': 6, # Kurtosis of signal (standardization units and seconds)
    }

## Colors
## Note: This cmap only has 6 pairs
## If going >6 clusters you will need to add additional pairs in.
## Pairs are 2-tuples of RGB 3-tuples
paired_cmap = mpl.colormaps['Paired']
colors = [paired_cmap((i+0.5)/12) for i in range(12)]
color_pairs = [ (colors[i+1], colors[i]) for i in range(0,12,2) ]
## Use tab20 instead (10 pairs)
## The color "blend" of this one is worse tho, so use paired where possible
# tab20_cmap = mpl.colormaps['tab20']
# colors = [tab20_cmap((i+0.5)/20) for i in range(20)]
# color_pairs = [ (colors[i], colors[i+1]) for i in range(0,20,2) ]


separated = load_separated_by_meta('signed_voltage', *files)
for volt, datasets in separated.items():
    if volt not in [
            0.3,
            0.4,
            0.5
            ]:
        continue # This means skip
    
    tabprint0('Voltage:', volt)
    dataset = combine_datasets(*datasets) # Should only be 1 for 100ksps, but 40Msps will have multiple
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
    # X_clustering = np.concatenate( (X_fullres, X_geoplus), axis=1)
    
    ## RNG
    # seed = time.time_ns() // 100 % 1_000_000_000
    seed = 0
    # rng = np.random.RandomState(seed)
    rng = seed
    if type(rng) == int:
        tabprint1(f'RNG: {seed}')
    else:
        tabprint1(f'RNG: RandomState({seed})')
        
    ## Init
    n_clusters = 4 # Starting n_clusters
    last_max_pcorr = 0.0 # Do not edit
    while n_clusters >= 4: # Min n_clusters
        tabprint1('N clusters:', n_clusters)
        
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
        tabprint2('Cluster sizes:', cluster_sizes)
        tabprint2('Largest cluster:', largest_cluster)

        ## Stats
        ## Pairwise similarities (pearson coeff) between each cluster centers
        tabprint2('- Pairwise similarities -')
        pcorrs = []
        for i in range(len(cluster_centers)):
            for j in range(len(cluster_centers)):
                if j> i:
                    pcorr = stats.pearsonr(cluster_centers[i], cluster_centers[j])[0]
                    pcorrs.append(pcorr)
                    tabprint2(i,j,pcorr)
        max_pcorr = max(pcorrs) if len(pcorrs) > 0 else 0.0 # Similarity value of the most similar pair of cluster centers
        tabprint2('Similarity of most similar pair:', max_pcorr)
        
        ## Select what to display
        # X_display = X_clustering
        X_display = X_fullres
        # X_display = X_ml
        
        ## Get members' display part
        cluster_members = {}
        for i in range(len(cluster_centers)):
            ind = kmeans.labels_ == i
            cluster_members[i] = X_display[ind, :]
        
        ## Do display
        plt.figure()
        # plt.subplot(2,3,n_clusters_idx+1)
        i_idx = 0 # i_idx is idx of cluster in sorted by size. i is "cluster ID"
        for i, cluster_size in sorted(cluster_sizes.items(), key=lambda item: item[1], reverse=True):
            # if i_idx != 0: # Only plot first cluster
            if i_idx > 4: # Only plot first N clusters
            # if False: # Plot all clusters
                break
            cluster_center = cluster_centers[i]
            members = cluster_members[i]
            color_pair = color_pairs[i_idx]
            center_color, members_color = color_pair
            plt.plot(
                cluster_center, 
                color=center_color, 
                # label=f'Cluster#{i} (Size:{cluster_size})', # Label i (ID)
                label=f'Cluster {i_idx} (Size:{cluster_size})', # Label i_idx (Numbered by size)
                zorder=100+i_idx # Dont edit this (100 makes centers above members, +i_idx means later/smaller clusters draw oever earlier/larger clusters)
                )
            # if i_idx == 0: # Only plot members of this cluster
            if True: # Plot members for all clusters
                for j in range(len(members)):
                    if freq == '40M':
                        if j % 5 != 0: # Plot only every Nth member
                            continue
                    member = members[j]
                    plt.plot(
                        member, 
                        color=members_color, 
                        alpha=0.15
                        
                        , 
                        linewidth=0.08, 
                        zorder=i_idx # Dont edit this
                        )
            i_idx += 1 # Dont edit this
        #plt.title(f'{n_clusters}')
        #plt.suptitle(f'{volt}')
        plt.legend(loc='upper right',fontsize = 9)
        plt.ylabel(r'Sqrt[ΔG G₀] (nS) ',fontsize=13)
        plt.xlabel('Δt(ms)',fontsize=13)
        plt.xticks([0,50,100,150,200,250,300,350,400],['-0.5','-0.375','-0.25','-0.125','0.0','0.125','0.25','0.375','0.5'],fontsize=10)
        plt.yticks(fontsize=11)
        #plt.ylim([0, 80])
        plt.ylim(bottom=0)
        plt.title(f'Voltage: {volt*1000} mV',fontsize = 10)
        
        ## Termination condition
        delta_max_pcorr = last_max_pcorr - max_pcorr # max_pcorr from last n_cluster's iteration - max_pcorr from current n_cluster's iteration
        
        tabprint2('Change in max similarity:', delta_max_pcorr)
        # if max_pcorr < 0.85: # Stop when all cluster centers below centain similarity value
        #     break
        # if abs(delta_max_pcorr) < 0.1: # Stop when converge (as measured by small change in max_pcorr) WARNING: If too small you can overshoot true convergence and end up going to min n_cluster
        #     break
        # if n_clusters <= 4 and max_pcorr < 0.85: # Additionally enforce a max n_cluster
        #     break
    
        ## Loop contiuation matters
        n_clusters -= 1
        last_max_pcorr = max_pcorr

# BSA 500mV 4
# HSA 500mV 4
# ConA 500mV 4
# BovineHb 500mV 4