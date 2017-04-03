#!/usr/bin/python
# encoding=utf8
import json
import logging
import urllib
import uuid
from selenium import webdriver

import requests

from ..exception import ExistingError
from ..utils import dictUtils, fileUtils, textUtils

logger = logging.getLogger(__name__)


class CrawlerBrowser(object):
  CHROME, FIREFOX, IE, EDGE = range(4)

  @staticmethod
  def get_useragent(browser):
    if browser == CrawlerBrowser.CHROME:
      return 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/57.0.2987.110 Safari/537.36'
    if browser == CrawlerBrowser.IE:
      return 'Mozilla/5.0 (Windows NT 6.3; WOW64; Trident/7.0; Touch; rv:11.0) like Gecko'
    if browser == CrawlerBrowser.EDGE:
      return 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.79 Safari/537.36 Edge/14.14393'
    return 'Mozilla/5.0 (Windows NT x.y; Win64; x64; rv:10.0) Gecko/20100101 Firefox/10.0'

  @staticmethod
  def get_driver(browser):
    execPath = 'C:/Users/tts/Projects/private/athletic-teacher/athletic/exec'
    if browser == CrawlerBrowser.CHROME:
      return webdriver.Chrome(executable_path=fileUtils.joinPaths(execPath, 'chromedriver.exe'))
    if browser == CrawlerBrowser.IE:
      return webdriver.Ie(executable_path=fileUtils.joinPaths(execPath, 'IEDriverServer.exe'))
    if browser == CrawlerBrowser.EDGE:
      return webdriver.Edge(executable_path=fileUtils.joinPaths(execPath, 'MicrosoftWebDriver.exe'))
    return webdriver.Firefox(executable_path=fileUtils.joinPaths(execPath, 'geckodriver.exe'))


class CrawlerAction(object):
  SEARCH, ACCESS, COMPLETE, FULL = range(4)


class CrawlerState(object):
  OK, ERROR, SUSPICION = range(3)


class Crawler(object):

  def __init__(self, dao, searchQuery, interval=10):
    self.dao = dao
    self.interval = interval
    self.delay = 1
    self.searchQuery = searchQuery
    self.tempPrefix = fileUtils.joinPaths('athletic', searchQuery.get('method').get('type'))
    self.account = searchQuery.get('method').get('auth').get('user') if searchQuery.get('method').get('auth') else None
    self.password = searchQuery.get('method').get('auth').get(
        'password') if searchQuery.get('method').get('auth') else None
    self.locations = searchQuery.get('query').get('locations')
    self.keywords = searchQuery.get('query').get('keywords')
    self.counter = dictUtils.deep_copy(searchQuery.get('counter'))
    self.socialRegex = {
        'email': r'[a-z][a-z0-9_\-\.]+@([a-z0-9\-]+\.)+[a-z]{2,4}',
        'facebook': r'(https?://)?(www\.)?(mbasic.facebook|m\.facebook|facebook|fb)\.(com|me)/(?:(?:\w\.)*#!\/)?(?:pages\/)?(?:[\w\-\.]+\/)*([\w\-\.]+)',
        'flickr': r'(https?://)?(www\.)?flickr\.com/([\w\-\.]+)',
        'github': r'(https?://)?(www\.)?github\.com/([\w\-\.]+)',
        'gplus': r'(https?://)?plus\.google\.com/([\w\-\.]+)',
        'instagram': r'(https?://)?(www\.)?(instagram.com|instagr.am)/([a-z0-9_\-]{2,})/?',
        'linkedin': r'(https?://)?(www\.)?linkedin\.com/in/[a-z0-9_\-]+\/?',
        'pinterest': r'(https?://)?(www\.)?pinterest\.com/([\w\-\.]+)',
        'twitter': r'(https?://)?twitter\.com\/(?:(#!\/)?(?:[\w\-\.]+\/)*([\w\-\.]+))',
        'youtube': r'(https?://)?(www\.)?youtube\.com/(channel\/|user\/)?[a-zA-Z0-9\-]+',
        'phone': {
            'prefix': r'(telephone|phone|mobile|tel|call|call us)(\s?:|\s?-)?(?i)',
            'regex': r'^(?:(?:\(?(?:00|\+)([1-4]\d\d|[1-9]\d?)\)?)?[\-\.\s\\\/]?)?((?:\(?\d{1,}\)?[\-\.\ \\\/]?){0,})(?:[\-\.\ \\\/]?(?:#|ext\.?|extension|x)[\-\.\ \\\/]?(\d+))?$(?i)'
        }
    }

  def connectURL(self, url):
    server = 'http://192.168.182.128:8050/render.html'
    payload = {'url': url, 'timeout': self.interval, 'wait': self.delay, 'images': 0}
    logger.info('Conntect to server::{} - payload::{}'.format(server, payload))
    response = requests.get(server, params=payload)
    code = response.status_code
    contentType = response.headers['content-type']
    content = response.json() if contentType == 'application/json' else response.text
    logger.info('Response from server::{} - payload::{} - status::{} - type::{}'.format(server, payload, code, contentType))
    return code == 200, content

  def search(self):
    ''' Search and collect simple profile '''
    logger.info('== Params == l: {} - k: {} - c: {}'.format(self.locations,
                                                            self.keywords, self.counter))
    runId = self.track(CrawlerAction.SEARCH)
    self.finish(runId, self.search0(runId))

  def access(self):
    ''' Collect intensively detail profile '''
    records = self.dao.list('teachers', {
        '$and': [
            {'metadata.method': self.searchQuery.get('method').get('type')},
            {'specialist': {'$in': [k.get('specialist') for k in self.searchQuery.get('query').get('keywords')]}},
            {
                '$or': [
                    {'location': {'$in': self.searchQuery.get('query').get('locations')}},
                    {'location': {'$exists': False}},
                ]
            },
            {
                '$or': [
                    {'metadata.action': CrawlerAction.SEARCH},
                    {
                        'metadata.action': CrawlerAction.ACCESS,
                        'metadata.state': {'$nin': [CrawlerState.ERROR, CrawlerState.OK], '$exists': True}
                    }
                ]
            }
        ]
    }, fields=[], limit=self.counter.get('access').get('limited'))
    runId = self.track(CrawlerAction.ACCESS)
    self.access0(runId, records)

  def complete(self, func):
    ''' Collect profile from external resource(facebook/google) '''
    query = {
        'metadata.method': self.searchQuery.get('method').get('type'),
        'website': {'$exists': True, '$ne': [], '$ne': None},
        'metadata.action': CrawlerAction.ACCESS,
        'specialist': {'$in': [k.get('specialist') for k in self.searchQuery.get('query').get('keywords')]},
        # '$or': [
        #     {},
        #     {
        #         'metadata.action': CrawlerAction.COMPLETE,
        #         'metadata.state': {'$nin': [CrawlerState.OK], '$exists': True}
        #     }
        # ]
    }
    query = dictUtils.merge_dicts(True, self.searchQuery.get('query').get('additional'), query)
    records = self.dao.list('teachers', query, fields=[], limit=-1)
    runId = self.track(CrawlerAction.COMPLETE, json.dumps(query))
    self.finish(runId, func.access0(runId, records))

  def search0(self, runId):
    raise NotImplementedError("Must implement")

  def access0(self, runId, records):
    raise NotImplementedError("Must implement")

  def complete0(self, runId, records):
    raise NotImplementedError("Must implement")

  def track(self, action, query=''):
    runId = str(uuid.uuid4())
    trackRecord = {
        'runId': runId,
        'action': action,
        'method': self.searchQuery.get('method').get('type'),
        'requestBy': self.searchQuery.get('requestBy'),
        'scrapeBy': self.account,
        'total': 0,
        'query': query
    }
    logging.info('Start RunId: {}'.format(runId))
    self.dao.insertOne('crawler_transactions', trackRecord)
    return runId

  def finish(self, runId, result):
    logging.info('Finish RunId: {} - Total: {} - Count: {} - Errors: {}'.format(runId,
                                                                                result.get('total'),
                                                                                result.get('count'),
                                                                                len(result.get('errors'))))
    self.dao.update('crawler_transactions', {'runId': runId}, data=result)

  def processEntity(self, runId, entity, action=CrawlerAction.SEARCH):
    if textUtils.isEmpty(entity.get('fullName')):
      entity['fullName'] = entity.get('firstName', '') + ' ' + entity.get('lastName', '')
    if 'metadata' not in entity:
      entity['metadata'] = {}
    entity['metadata']['action'] = action
    entity['metadata']['method'] = self.searchQuery.get('method').get('type')
    query = {'key': entity.get('key'), 'metadata.method': entity.get('metadata').get('method')}
    logger.info('Process entity: {}'.format(query))
    logger.debug('==> Entity: {}'.format(entity))
    existed = self.dao.findOne('teachers', query)
    if existed is not None:
      logging.info('Update keywords metadata for existed entity: {}'.format(query))
      arrays = self.dao.buildSetValues({
          'metadata.keywords': entity.get('metadata').get('keywords'),
          'metadata.runId': [runId]
      })
      self.dao.update('teachers', query, arrays=arrays)
    else:
      entity['metadata']['runId'] = [runId]
      self.dao.insertOne('teachers', entity)

  def updateRecordState(self, runId, record, state=None, action=None):
    if state is None:
      state = record.get('metadata.state')
      state = CrawlerState.ERROR if CrawlerState.SUSPICION == state else CrawlerState.SUSPICION
    searchMethod = self.searchQuery.get('method').get('type')
    recordMethod = record.get('metadata').get('method')
    self.updateEntity(runId, record, action=action, state=state)

  def updateEntity(self, runId, record, entity={}, arrays={}, action=CrawlerAction.ACCESS, state=CrawlerState.OK):
    method = self.searchQuery.get('method').get('type')
    if 'metadata' not in entity:
      entity['metadata'] = {}
    entity['metadata']['action'] = action
    entity['metadata']['method'] = method
    entity['metadata']['state'] = state
    arrays = dictUtils.merge_dicts(True, {'metadata.runId': [runId]}, dictUtils.flatten(arrays))
    arrayValues = self.dao.buildSetValues(arrays)
    key = record.get('key')
    logger.info('Update entity: {}@{}'.format(method, urllib.quote_plus(textUtils.encode(record.get('key')))))
    logger.debug('==> Entity::{} - Arrays::{}'.format(entity, arrays))
    query = {'key': key, 'metadata.method': method}
    self.dao.update('teachers', query, data=entity, arrays=arrayValues)

  def detectWebsiteType(self, url):
    for key, regex in self.socialRegex.iteritems():
      if key == 'phone':
        continue
      if textUtils.match(url, regex):
        return {key: url}
    return {'website': url}

  def findSocials(self, textData):
    socials = {}
    for key, regex in self.socialRegex.iteritems():
      regex = regex if key != 'phone' else (regex.get('prefix') + regex.get('regex'))
      value = textUtils.search(textData, regex)
      if value:
        socials[key] = value
    return socials
