#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Code for parsing and visualising financial vehicle corporation (FVC)
data publised by ESMA.

Usage:
    fvc.py <path_to_shapefile> <path_to_fvc_list> <path_to_save_map_to>
"""

import sys

import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
from matplotlib.cm import ScalarMappable

# SHP_FPATH should be a path to a shapefile (.shp) with geodata for (at least) the euro area countries.
# See https://ec.europa.eu/eurostat/web/gisco/geodata/reference-data/administrative-units-statistical-units/countries
SHP_FPATH = sys.argv[1]
FVC_LIST_PATH = sys.argv[2]
OUTPUT_FILE = sys.argv[3]

TITLE = 'Number of financial vehicle corporations'

# Let's restrict our analysis to the eurozone countries

EUROZONE = {'AT', 'BE', 'CY', 'EE', 'FI', 'FR', 'DE', 'GR', 'IE', 'IT',
            'LV', 'LT', 'LU', 'MT', 'NL', 'PT', 'SK', 'SI', 'ES'}

# Coordinates to zoom the map to Europe
# (x1, y1) = bottom-left; (xy, y2) = top-right

x1 = -1353606.4502846375
x2 = 4026444.456398748
y1 = 4035301.5413707625
y2 = 9453374.009232119

map_df = gpd.read_file(SHP_FPATH).set_index('CNTR_ID')
map_df = map_df[map_df.index.isin(EUROZONE)]

# Every entry in the FVC data should have a value in the "ID" column, so that is what we should count
fvc_counts = pd.read_excel(FVC_LIST_PATH).groupby('Country of residence').count()['ID']
fvc_counts = fvc_counts[fvc_counts.index.isin(EUROZONE)].rename(TITLE)
map_df = map_df.join(fvc_counts)

vmin = 0
vmax = fvc_counts.max()


fig, ax = plt.subplots(1, 1)
        
ax.axis('off')
ax.set_title(TITLE)
ax.annotate('Source: ECB data, Q2 2020', xy=(0.1, .08), xycoords='figure fraction', horizontalalignment='left',
            verticalalignment='bottom', fontsize=10, color='#555555')
        
ax.set_xlim(x1, x2)
ax.set_ylim(y1, y2)
        
norm = Normalize(vmin=0, vmax=fvc_counts.max())
mapper = ScalarMappable(norm=norm, cmap='Blues')
plt.colorbar(mapper)
    
map_df.plot(column=TITLE, ax=ax, cmap='Blues')
map_df.boundary.plot(ax=ax, linewidth=0.4)
        
fig.savefig(OUTPUT_FILE, dpi=300)
    
