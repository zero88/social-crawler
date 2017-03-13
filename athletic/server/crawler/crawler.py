import logging
import urllib
import uuid

from ..exception import ExistingError
from ..utils import dictUtils, textUtils

logger = logging.getLogger(__name__)


class CrawlerAction(object):
  SEARCH, ACCESS, COMPLETE, FULL = range(4)


class CrawlerState(object):
  OK, ERROR, SUSPICION = range(3)


class Crawler(object):

  def __init__(self, dao, searchQuery, interval=30):
    self.dao = dao
    self.interval = interval
    self.searchQuery = searchQuery
    self.account = searchQuery.get('method').get('auth').get('user')
    self.password = searchQuery.get('method').get('auth').get('password')
    self.locations = searchQuery.get('query').get('locations')
    self.keywords = searchQuery.get('query').get('keywords')
    self.counter = dictUtils.deep_copy(searchQuery.get('counter'))
    self.socialRegex = {
        'facebook': r'((http|https)://)?(www\.)?facebook\.com/.+',
        'flickr': r'((http|https)://)?(www\.)?flickr\.com/.+',
        'github': r'((http|https)://)?(www\.)?youtube\.com/.+',
        'gplus': r'((http|https)://)?plus\.google\.com/.+',
        'instagram': r'((http|https)://)?(www\.)?instagram\.com/.+',
        'linkedin': r'((http|https)://)?(www\.)?linkedin\.com/.+',
        'pinterest': r'((http|https)://)?(www\.)?pinterest\.com/.+',
        'twitter': r'((http|https)://)?twitter\.com/.+'
    }

  def search(self):
    ''' Search and collect simple profile '''
    logger.info('== Params == l: {} - k: {} - c: {}'.format(self.locations,
                                                            self.keywords, self.counter))
    runId = self.track(CrawlerAction.SEARCH)
    self.finishTrack(runId, self.search0(runId))

  def access(self):
    ''' Collect intensively detail profile '''
    records = self.dao.list('teachers', {
        'metadata.method': self.searchQuery.get('method').get('type'),
        '$or': [
            {'metadata.action': CrawlerAction.SEARCH},
            {
                'metadata.action': CrawlerAction.ACCESS,
                'state': {'$nin': [CrawlerState.ERROR, CrawlerState.OK], '$exists': True}
            }
        ]
    }, limit=-1)
    runId = self.track(CrawlerAction.ACCESS)
    self.finishTrack(runId, self.access0(runId, records))

  def complete(self):
    ''' Collect profile from external resource(facebook/google) '''
    self.complete0(self.track(CrawlerAction.COMPLETE))

  def search0(self, runId):
    raise NotImplementedError("Must implement")

  def access0(self, runId, record):
    raise NotImplementedError("Must implement")

  def complete0(self, runId):
    raise NotImplementedError("Must implement")

  def track(self, action):
    runId = str(uuid.uuid4())
    trackRecord = {
        'runId': runId,
        'action': action,
        'method': self.searchQuery.get('method').get('type'),
        'requestBy': self.searchQuery.get('requestBy'),
        'scrapeBy': self.account,
        'total': 0,
        'stopAt': []
    }
    logging.info('Start track runId: {}'.format(runId))
    self.dao.insertOne('crawler_transactions', trackRecord)
    return runId

  def finishTrack(self, runId, result):
    logging.info('Finish track runId: {}'.format(runId))
    self.dao.update('crawler_transactions', {'runId': runId}, data=result)

  def processEntity(self, runId, entity, action):
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

  def updateEntity(self, runId, record, entity, action):
    method = self.searchQuery.get('method').get('type')
    if 'metadata' not in entity:
      entity['metadata'] = {}
    entity['metadata']['action'] = action
    entity['metadata']['method'] = method
    arrays = self.dao.buildSetValues({
        'metadata.runId': [runId]
    })
    key = record.get('key')
    logger.info('Update entity: {}@{}'.format(method, urllib.quote_plus(textUtils.encode(record.get('key')))))
    logger.debug('==> Entity: {}'.format(entity))
    query = {'key': key, 'metadata.method': method}
    self.dao.update('teachers', query, data=entity, arrays=arrays)

  def parseWebsite(self, url):
    for key, regex in self.socialRegex.iteritems():
      if textUtils.match(url, regex):
        return {key: url}
    return {'website': url}
