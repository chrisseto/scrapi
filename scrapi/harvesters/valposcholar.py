"""
Harvester for ValpoScholar for the SHARE NS
"""

from __future__ import unicode_literals

from scrapi.base import OAIHarvester


class ValpoScholarHarvester(OAIHarvester):
    short_name = 'valposcholar'
    long_name = 'Valparaiso University ValpoScholar'
    url = 'http://scholar.valpo.edu/'

    base_url = 'http://scholar.valpo.edu/do/oai/'
    property_list = [
        'type', 'source', 'setSpec',
        'format', 'identifier', 'publisher'
    ]
    approved_sets = [
        'cc_fac_pub',
        'it_pubs',
        'ccls_fac_pub',
        'journaloftolkienresearch',
        'art_fac_pub',
        'bio_fac_pub',
        'chem_fac_pub',
        'comm_fac_pubs',
        'econ_fac_pub',
        'ed_fac_pubs',
        'eng_fac_pub', 'vfr',
        'german_fac_pub',
        'spanish_fac_pub',
        'geomet_fac_pub',
        'history_fac_pub',
        'kin_fac_pubs',
        'mcs_fac_pubs',
        'phys_astro_fac_pub',
        'poli_sci_fac_pubs',
        'psych_fac_pub',
        'sociology_fac_pub',
        'theatre_fac_pubs',
        'theo_fac_pubs',
        'cba_fac_pub',
        'jvbl',
        'engineering_fac_pub',
        'ebpr',
        'msn_theses',
        'nursing_fac_pubs',
        'grad_student_pubs',
        'vulr',
        'law_fac_pubs',
        'ils_papers'
    ]
