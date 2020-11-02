#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Code for accessing the Global LEI Index API operated by the Global
Legal Entity Identifier Foundation.
"""

import json
from urllib.request import urlopen
from typing import Dict, Sequence

LEI_LOOKUP_URL = 'https://api.gleif.org/api/v1/lei-records?page[size]={n}&page[number]=1&filter[lei]={lei}'

def lookup_entity_api(leis: Sequence[str]) -> Dict[str, Dict[str, str]]:
    """Fetch company name and country for each LEI in `leis` using the
    GLEIF API. Returns a dict mapping each LEI to a dict containing
    the relevant data.
    """

    url = LEI_LOOKUP_URL.format(n=len(leis), lei=','.join(leis))
    request = urlopen(url)
    lei_records = json.load(request)['data']
    data = {}
    for record in lei_records:
        attr = record['attributes']
        data[attr['lei']] = {
            'name': attr['entity']['legalName']['name'],
            'country': attr['entity']['jurisdiction']
        }
    return data
