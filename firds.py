#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""A few functions to download and access data from ESMA's Financial
Instrument Reference Data System (FIRDS).
"""

import os
import sqlite3 as sql
from datetime import datetime, timedelta
from zipfile import ZipFile
from io import BytesIO
from typing import Dict, Optional, List, Iterable

import requests
from lxml import etree


### The functions below are helper functions to download and extract FIRDS XML data.

FIRST_FIRDS_DATE = datetime(2017, 10, 15)  # Apparently the earliest date on which there are any FIRDS files.
DATA_DIR = 'data_files'
Q_URL = ('https://registers.esma.europa.eu/solr/esma_registers_firds_files/'
         'select?q=*&fq=publication_date:%5B{from_year}-{from_month}-'
         '{from_day}T00:00:00Z+TO+{to_year}-{to_month}-{to_day}T23:59:59Z%5D'
         '&wt=xml&indent=true&start={start}&rows={rows}')
FNAME_START = 'FULINS_{}'


def _request_file_urls(from_date: datetime, to_date: datetime, start, rows) -> etree._Element:
    """Request data on FIRDS files (including download URLs) for the
    given timeframe and return the XML object.
    """

    url = Q_URL.format(
        from_year=from_date.year,
        from_month=from_date.month,
        from_day=from_date.day,
        to_year=to_date.year,
        to_month=to_date.month,
        to_day=to_date.day,
        start=start,
        rows=rows
    )
    response = requests.get(url)
    return etree.fromstring(response.content)


def _parse_file_urls(root: etree._Element, ftype: str = '') -> List[str]:
    """Takes an XML element with FIRDS file data (such as that returned
    by _request_file_urls) and returns download URLs for all relevant
    files.

    `ftype`, if given, should be the first letter of the CFI code for
    the relevant security type (eg, 'B' for bonds), or a string of such
    letters (eg, "BE" for bonds and equities). In that case only URLs
    for files of the specified type(s) will be included.
    """

    urls = []

    for entry in root[1]:
        fname = entry.xpath('.//str[@name="file_name"]')[0].text
        if (not ftype) or any(fname.startswith(FNAME_START.format(f)) for f in ftype):
            url = entry.xpath('.//str[@name="download_link"]')[0].text
            urls.append(url)

    return urls


def get_file_urls(from_date: datetime = None, to_date: datetime = None, ftype: str = '') -> List[str]:
    """Get the download URLs for all FIRDS files within the given
    timeframe, for the given security type (if provided).
    """
    
    start = 0
    rows = 100
    
    if from_date is None:
        to_date = datetime.today()
        from_date = to_date - timedelta(weeks=1)
    elif to_date is None:
        to_date = from_date
    
    root = _request_file_urls(from_date, to_date, start, rows)
    num_results = int(root[1].attrib['numFound'])
    urls = _parse_file_urls(root, ftype)
    
    while num_results > (start + rows):
        start += rows
        root = _request_file_urls(from_date, to_date, start, rows)
        urls += _parse_file_urls(root, ftype)
    
    return urls
    
def download_zipped_file(url: str, to_dir: str) -> str:
    """Download a zip file from `url` and extract the contents to `to_dir`.
    returns the path to the extracted file (this assumes there is only one
    file in the zip archive).
    """
    
    if not os.path.exists(to_dir):
        os.makedirs(to_dir)
        
    response = requests.get(url)
    response.raise_for_status()
    zipfile = ZipFile(BytesIO(response.content))
    name = zipfile.namelist()[0]
    zipfile.extractall(path=to_dir)
    
    return os.path.join(to_dir, name)
    
def get_xml_files(ftype: str = '',
                  data_dir: str = '.',
                  from_date: Optional[datetime] = None, 
                  to_date: Optional[datetime] = None,
                  force_dl: bool = False) -> List[str]:
    """Download and extract all FIRDS XML files for the given security
    type and timeframe. Returns a list of filepaths.
    """
    
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)

    urls = get_file_urls(from_date, to_date, ftype=ftype)
    fpaths = [download_zipped_file(url, data_dir) for url in urls]
    return fpaths

### The following functions are used create an ISIN->LEI lookup table based on the FIRDS data.

DEFAULT_DB_FILE = 'firds.db'

ns = {
    'BizData': 'urn:iso:std:iso:20022:tech:xsd:head.003.001.01',
    'AppHdr': 'urn:iso:std:iso:20022:tech:xsd:head.001.001.01',
    'Document': 'urn:iso:std:iso:20022:tech:xsd:auth.017.001.02'
}

CREATE_TABLE = """CREATE TABLE IF NOT EXISTS \"{table}\" (
    isin TEXT PRIMARY KEY,
    lei TEXT NOT NULL
)"""


def append_to_table(table: str, xml_file: str, db_file: str = DEFAULT_DB_FILE):
    """Create a table with name `table`, if it does not already exist,
    and insert ISIN/LEI pairs for each security described in `xml_file`.
    """
    
    conn = sql.connect(db_file)
    cursor = conn.cursor()
    cursor.execute(CREATE_TABLE.format(table=table))
    tree = etree.parse(xml_file)
    root = tree.getroot()
    args = []
    #print(root.xpath('Document:RefData', namespaces=ns))
    for ref_data in root.xpath('//Document:RefData', namespaces=ns):
        isin = ref_data.xpath('Document:FinInstrmGnlAttrbts/Document:Id', namespaces=ns)[0].text
        lei = ref_data.xpath('Document:Issr', namespaces=ns)[0].text
        #print(isin, lei)
        #cursor.execute(f'INSERT OR IGNORE INTO "{table}" (isin, lei) VALUES (?, ?)', (isin, lei))
        args.append((isin, lei))
    cursor.executemany(f'INSERT OR IGNORE INTO "{table}" (isin, lei) VALUES (?, ?)', args)
    conn.commit()
    
def lookup_leis(isins: Iterable[str], table: str, db_file: str = DEFAULT_DB_FILE) -> List[str]:
    """Looks up each ISIN code in `isins` in `table` to find its
    corresponding issuer LEI. Returns a list of LEIs in the same
    order as `isins`. Where an LEI is not found, None appears at
    the relevant index of the list.
    """
    
    conn = sql.connect(db_file)
    cursor = conn.cursor()
    results = []
    for i in isins:
        cursor.execute(f'SELECT lei FROM "{table}" WHERE isin=?', (i,))
        results.append(cursor.fetchone()[0])
    return results
