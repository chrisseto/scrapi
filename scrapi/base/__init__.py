# Classes for scrAPI Harvesters
from __future__ import unicode_literals

import abc
import logging
from datetime import date, timedelta

from lxml import etree
from celery.schedules import crontab

from scrapi import util
from scrapi import requests
from scrapi.linter import lint
from scrapi.base.schemas import OAISCHEMA
from scrapi.base.helpers import updated_schema
from scrapi.base.transformer import XMLTransformer
from scrapi.linter.document import RawDocument, NormalizedDocument

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)


class _Registry(dict):

    def __init__(self):
        super(_Registry, self).__init__()

    def __getitem__(self, key):
        try:
            return super(_Registry, self).__getitem__(key)
        except KeyError:
            raise KeyError('No harvester named "{}"'.format(key))

    @property
    def beat_schedule(self):
        return {
            'run_{}'.format(name): {
                'args': [name],
                'schedule': crontab(**inst.run_at),
                'task': 'scrapi.tasks.run_harvester',
            }
            for name, inst
            in self.items()
        }

registry = _Registry()


class HarvesterMeta(abc.ABCMeta):
    def __init__(cls, name, bases, dct):
        super(HarvesterMeta, cls).__init__(name, bases, dct)
        if len(cls.__abstractmethods__) == 0:
            registry[cls.short_name] = cls()
        else:
            logger.info('Class {} not added to registry'.format(cls.__name__))


class BaseHarvester(object):
    """ This is a base class that all harvesters should inheret from

    Defines the copy to unicode method, which is useful for getting standard
    unicode out of xml results.
    """
    __metaclass__ = HarvesterMeta

    @abc.abstractproperty
    def short_name(self):
        raise NotImplementedError

    @abc.abstractproperty
    def long_name(self):
        raise NotImplementedError

    @abc.abstractproperty
    def url(self):
        raise NotImplementedError

    @abc.abstractproperty
    def file_format(self):
        raise NotImplementedError

    @abc.abstractmethod
    def harvest(self, days_back=1):
        raise NotImplementedError

    @abc.abstractmethod
    def normalize(self, raw_doc):
        raise NotImplementedError

    def lint(self):
        return lint(self.harvest, self.normalize)

    @property
    def run_at(self):
        return {
            'hour': 22,
            'minute': 59,
            'day_of_week': 'mon-fri',
        }


class XMLHarvester(BaseHarvester, XMLTransformer):
    file_format = 'xml'

    def normalize(self, raw_doc):
        transformed = self.transform(etree.XML(raw_doc['doc']))
        transformed['source'] = self.short_name
        return NormalizedDocument(transformed)


class OAIHarvester(XMLHarvester):
    """ Create a harvester with a oai_dc namespace, that will harvest
    documents within a certain date range

    Contains functions for harvesting from an OAI provider, normalizing,
    and outputting in a way that scrapi can understand, in the most
    generic terms possible.

    For more information, see the OAI PMH specification:
    http://www.openarchives.org/OAI/openarchivesprotocol.html
    """
    record_encoding = None
    DEFAULT_ENCODING = 'UTF-8'
    RESUMPTION = '&resumptionToken='
    RECORDS_URL = '?verb=ListRecords'
    META_PREFIX_DATE = '&metadataPrefix=oai_dc&from={}'

    # Override these variable is required
    namespaces = {
        'dc': 'http://purl.org/dc/elements/1.1/',
        'ns0': 'http://www.openarchives.org/OAI/2.0/',
        'oai_dc': 'http://www.openarchives.org/OAI/2.0/',
    }

    timeout = 0.5
    approved_sets = None
    timezone_granularity = False
    property_list = ['date', 'language', 'type']

    @property
    def schema(self):
        properties = {
            'properties': {
                item: (
                    '//dc:{}/node()'.format(item),
                    '//ns0:{}/node()'.format(item),
                    self.resolve_property
                ) for item in self.property_list
            }
        }
        return updated_schema(OAISCHEMA, properties)

    def resolve_property(self, dc, ns0):
        if isinstance(dc, list) and isinstance(ns0, list):
            ret = dc.extend(ns0)
            return [val for val in ret if val]
        elif not dc:
            return ns0
        elif not ns0:
            return dc
        else:
            return [dc, ns0]

    def harvest(self, days_back=1):

        start_date = str(date.today() - timedelta(int(days_back)))

        records_url = self.base_url + self.RECORDS_URL
        request_url = records_url + self.META_PREFIX_DATE.format(start_date)

        if self.timezone_granularity:
            request_url += 'T00:00:00Z'

        records = self.get_records(request_url, start_date)

        rawdoc_list = []
        for record in records:
            doc_id = record.xpath(
                'ns0:header/ns0:identifier', namespaces=self.namespaces)[0].text
            record = etree.tostring(record, encoding=self.record_encoding)
            rawdoc_list.append(RawDocument({
                'doc': record,
                'source': util.copy_to_unicode(self.short_name),
                'docID': util.copy_to_unicode(doc_id),
                'filetype': 'xml'
            }))

        return rawdoc_list

    def get_records(self, url, start_date, resump_token=''):
        data = requests.get(url, throttle=self.timeout)

        doc = etree.XML(data.content)

        records = doc.xpath(
            '//ns0:record',
            namespaces=self.namespaces
        )
        token = doc.xpath(
            '//ns0:resumptionToken/node()',
            namespaces=self.namespaces
        )
        if len(token) == 1:
            base_url = url.replace(
                self.META_PREFIX_DATE.format(start_date), '')
            base_url = base_url.replace(self.RESUMPTION + resump_token, '')
            url = base_url + self.RESUMPTION + token[0]
            records += self.get_records(url, start_date, resump_token=token[0])

        return records

    def normalize(self, raw_doc):
        str_result = raw_doc.get('doc')
        result = etree.XML(str_result)

        if self.approved_sets:
            set_spec = result.xpath(
                'ns0:header/ns0:setSpec/node()',
                namespaces=self.namespaces
            )
            # check if there's an intersection between the approved sets and the
            # setSpec list provided in the record. If there isn't, don't normalize.
            if not {x.replace('publication:', '') for x in set_spec}.intersection(self.approved_sets):
                logger.info('Series {} not in approved list'.format(set_spec))
                return None

        status = result.xpath('ns0:header/@status', namespaces=self.namespaces)
        if status and status[0] == 'deleted':
            logger.info('Deleted record, not normalizing {}'.format(raw_doc['docID']))
            return None

        return super(OAIHarvester, self).normalize(raw_doc)
