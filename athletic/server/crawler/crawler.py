import logging
import uuid

from ..exception import ExistingError
from ..utils import textUtils

logger = logging.getLogger(__name__)


class CrawlerAction(object):
  SEARCH, ACCESS, COMPLETE, FULL = range(4)


class Crawler(object):

  def __init__(self, dao, searchQuery, interval=30):
    self.dao = dao
    self.interval = interval
    self.searchQuery = searchQuery
    self.account = searchQuery.get('method').get('auth').get('user')
    self.password = searchQuery.get('method').get('auth').get('password')
    self.locations = searchQuery.get('query').get('locations')
    self.keywords = searchQuery.get('query').get('keywords')
    self.max_item = searchQuery.get('query').get('total')

  def search(self):
    ''' Search and collect simple profile '''
    self.search0(self.track(CrawlerAction.SEARCH))

  def access(self):
    ''' Collect intensively detail profile '''
    self.access0(self.track(CrawlerAction.ACCESS))

  def complete(self):
    ''' Collect profile from external resource(facebook/google) '''
    self.access0(self.track(CrawlerAction.COMPLETE))

  def search0(self):
    raise NotImplementedError("Must implement")

  def access0(self):
    raise NotImplementedError("Must implement")

  def complete0(self):
    raise NotImplementedError("Must implement")

  def track(self, action):
    runId = str(uuid.uuid4())
    trackRecord = {
        'runId': runId,
        'action': action,
        'method': self.searchQuery.get('method').get('type'),
        'requestBy': self.searchQuery.get('requestBy')
    }
    self.dao.insertOne('crawler_transactions', trackRecord)
    return str(runId)

  def stopTrack(self, runId, keyword, location, page_index, url, message):
    stopAt = {
        'keyword': keyword,
        'location': location,
        'page_index': page_index,
        'url': url,
        'message': message
    }
    logging.info('Stopping runId: {}'.format(runId))
    arrays = self.dao.buildArrayAppendSet({'stopAt': [stopAt]})
    self.dao.update('crawler_transactions', {'runId': runId}, arrays=arrays)

  def processEntity(self, entity):
    if textUtils.isEmpty(entity.get('fullName')):
      entity['fullName'] = entity.get('firstName', '') + ' ' + entity.get('lastName', '')
    entity['metadata']['scrapeBy'] = self.account
    entity['metadata']['method'] = self.searchQuery.get('method').get('type')
    entity['metadata']['requestBy'] = self.searchQuery.get('requestBy')
    query = {'key': entity.get('key'), 'metadata.method': entity.get('metadata').get('method')}
    logger.info('Process entity: "{}"'.format(query))
    logger.debug('==> Entity: "{}"'.format(entity))
    existed = self.dao.findOne('teachers', query)
    if existed is not None:
      logging.info('Update keywords metadata for existed entity: {}'.format(query))
      arrays = self.dao.buildArrayAppendSet({'metadata.keywords': entity.get('metadata').get('keywords')})
      self.dao.update('teachers', query, arrays=arrays)
    else:
      self.dao.insertOne('teachers', entity)
