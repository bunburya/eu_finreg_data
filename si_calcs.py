#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Code for parsing and visualising trade volume data publised by ESMA.

Usage:
    si_calcs.py <path_to_excel_file> <path_to_save_graph_to>
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib import cm
import numpy as np

from firds import lookup_leis
from gleif import lookup_entity_api


def parse_si_calc_file(fpath: str, non_equity: bool = False) -> pd.DataFrame:
    """Parse the Excel file at `fpath` and return a DataFrame.
    `non_equity` should be True if the Excel file is a "Non-equity"
    file as published by ESMA.
    
    The resulting DataFrame will have the ISIN column as its index.
    """
    
    # The name of the worksheet we are looking for is different for the Non-equity file than for the Equities and
    # Bonds files.
    if non_equity:
        ws_name = 'Nb and volume of transactions'
    else:
        ws_name = 'SI calculations'
        
    df = pd.read_excel(fpath, sheet_name=ws_name, index_col='ISIN')
    
    # Some of the column headings can sometimes have leading or trailing whitespace, so strip it away.
    df.rename(columns=lambda col: col.strip(), inplace=True)
    
    return df

def plot_most_traded_stocks(df: pd.DataFrame, to_file: str, n: int = 20, turnover: bool = False,
                     title: str = None):
    """Generate a bar chart of of the `n` most traded securities in
    the EU. If `turnover` is true, total turnover is the metric used;
    otherwise, number of trades is the metric used.
    """
    
    # Determine what column to sort by, which will also determine the y values and the title of the plot
    if turnover:
        sort_col = 'Total turnover executed in the EU'
        scale = 1e9
        y_label = 'Turnover (€ billions)'
    else:
        sort_col = 'Total number of transactions executed in the EU'
        scale = 1e6
        y_label = 'Number of transactions (millions)'
    
    from_date = df['Calculation From Date'].iloc[0].strftime('%-d %B %Y')
    to_date = df['Calculation To Date'].iloc[0].strftime('%-d %B %Y')
    
    # Sort the entries in the DataFrame by transactions / turnover, and get the name and country of the company
    # corresponding to each ISIN code
    df = df.sort_values(sort_col, ascending=False).iloc[:n]
    df[sort_col] /= scale
    isins = df.index
    leis = lookup_leis(isins, 'equities')
    company_data = lookup_entity_api(leis)
    company_data_df = pd.DataFrame.from_dict(
        {isin: company_data[lei] for isin, lei in zip(isins, leis)},
        orient='index'
    )
    df = pd.concat([df, company_data_df], axis=1)
    
    # Colour the bars according to the country of incorporation of the company
    cmap = cm.get_cmap('Set1')
    countries = df['country'].unique().tolist()
    all_country_colors = cmap(np.linspace(0, 1, len(countries)))
    issuer_country_color = df['country'].map(lambda c: all_country_colors[countries.index(c)])
    patches = [mpatches.Patch(color=color, label=country) for color, country in zip(all_country_colors, countries)]
    
    
    fig, ax = plt.subplots(1)
    ax.bar(df['name'], df[sort_col], color=issuer_country_color)
    ax.legend(handles=patches, title='Country')
    plt.xticks(rotation=90)
    plt.ylabel(y_label)
    plt.title(f'Most traded stocks in the EU, {from_date} - {to_date}')
    ax.annotate('Source: ESMA Equity SI Calculations, 2020', xy=(0.0, 0.0), xycoords='figure fraction', horizontalalignment='left',
                verticalalignment='bottom', fontsize=9, color='#555555')
    
    plt.savefig(to_file, bbox_inches="tight")
    

if __name__ == '__main__':
    import sys
    df = parse_si_calc_file(sys.argv[1])
    plot_most_traded_stocks(df, sys.argv[2], turnover=True)
