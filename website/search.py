# -*- coding: utf-8 -*-
"""
    Search module for the scrAPI website.
"""
import copy
import json
import logging
import requests
import datetime

from scrapi import settings

logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

DEFAULT_PARAMS = {
    'q': '*',
    'start_date': None,
    'end_date': datetime.date.today().isoformat(),
    'sort_field': 'consumeFinished',
    'sort_type': 'desc',
    'from': 0,
    'size': 10,
    'format': 'json'
}


def query_osf(query):
    headers = {'Content-Type': 'application/json'}
    data = json.dumps(query)
    print data
    return requests.post(settings.OSF_APP_URL, auth=settings.OSF_AUTH, headers=headers, data=data).json()


def tutorial():
    return {
        'arguments': {
            'q': {
                'Description': 'The query parameter. Syntax specified by the Lucene query syntax',
                'More info': 'http://extensions.xwiki.org/xwiki/bin/view/Extension/Search+Application+Query+Syntax#HAND',
                'Examples' : ['open science AND source:PloS', 'open science NOT source:PLoS', 'title:open science AND (source:PLoS OR source:Scitech) NOT title:closed']
            },
            'start_date': {
                'Description': 'The beginning of a date range, formatted according to ISO 8601 (YYYY-MM-DD)',
                'More info': 'http://www.iso.org/iso/iso8601',
                'Examples': ['2014-08-31', '1999-01-17'],
            },
            'end_date': {
                'Description': 'The end of a date range, formatted according to ISO 8601 (YYYY-MM-DD)',
                'More info': 'http://www.iso.org/iso/iso8601',
                'Examples': ['2014-08-31', '1999-01-17'],
            },
            'sort_field': {
                'Description': 'A field on which to sort the results of a query.',
                'Examples': ['dateCreated', 'dateUpdated', 'consumeStarted'],
            },
            'sort_type': {
                'Description': 'Determines how a sort is ordered. Can be either "asc" (ascending) or "desc" (descending)',
                'Examples': ['asc', 'desc'],
            },
            'from': {
                'Description': 'For pagination, this is the index to start results.',
                'Examples': ['1', '10', '12', '141'],
            },
            'size': {
                'Description': 'The number of results that will be displayed at once',
                'Examples': ['0', '1', '10', '12', '25', '625'],
            },
        },
        'fields': {
            "given": "a string indicating the given name or initial of a contributor",
            "middle": "a string indicating the middle name or initial of a contributor",
            "family": "a string indicating the family name (surname) of a contributor",
            "prefix": "a string indicating a contributor's prefix (e.g. 'Dr.')",
            "suffix": "a string indicating a contributor's suffix (e.g. 'Jr.')",
            "email": "a string indicating the email address of a contributor",
            "dateCreated": "string indicating when the resource was first created or published using the format YYYY-MM-DD in iso format",
            "dateUpdated": "string indicating when the resource was last updated in the home repository using the format YYYY-MM-DD in iso format",
            "description": "an abstract or general description of the resource",
            "doi": "The digital object identifier of the resource, if it has one",
            "id": "a dictionary of unique IDs given to the resource based on the particular publication we're accessing; should include an entry for a URL that links to the original resource, a DOI, and a service specific ID",
            "serviceID": "a service-specific identifier for the resource",
            "source": "a string identifying the provider of the resource; this is a system ID, not the provider's full name (e.g. 'uceschol', not 'University of California eScholarship')",
            "tags": "a list of tags or keywords identified in the resource itself, normalized to be all lowercase",
            "timestamp": "string indicating when the resource was accessed by scrAPI using the format YYYY-MM-DD h : m : s in iso format",
            "title": "string representing title of the resource",
            "url": "a URL pointing to the resource's original location"
          },
    }


def search(raw_params):
    params = copy.deepcopy(DEFAULT_PARAMS)
    params.update(raw_params)
    for key in params.keys():
        if isinstance(params[key], list) and len(params[key]) == 1:
            params[key] = params[key][0]
    params['from'] = int(params['from'])
    params['size'] = int(params['size'])
    print params
    query = parse_query(params)
    query['format'] = params.get('format')
    return query_osf(query)


def parse_query(params):
    return {
        'query': build_query(
            params.get('q'),
            params.get('start_date'),
            params.get('end_date')
        ),
        'sort': build_sort(params.get('sort_field'), params.get('sort_type')),
        'from': params.get('from'),
        'size': params.get('size'),
    }


def build_query(q, start_date, end_date):
    return {
        'filtered': {
             'query': build_query_string(q),
             'filter': build_date_filter(start_date, end_date),
        }
    }


def build_query_string(q):
    return {
        'query_string': {
            'default_field': '_all',
            'query': q,
            'analyze_wildcard': True,
            'lenient': True  # TODO, may not want to do this
        }
    }


def build_date_filter(start_date, end_date):
    return {
        'range': {
            'consumeFinished': {
                'gte': start_date,  # TODO, can be None, elasticsearch may not like it
                'lte': end_date
            }
        }
    }

def build_sort(sort_field, sort_type):
    print sort_field
    return [{
        sort_field : {
            'order': sort_type
        }
    }]
