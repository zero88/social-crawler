import logging
import threading

from crawler.crawler import CrawlerAction
from crawler.factory import CrawlerFactory

from db import DAO, AthleticDB
from encrypt import Encrypt
from excel import ExcelWriteHandler
from utils import dictUtils, fileUtils

# from server import RESTServer

logger = logging.getLogger(__name__)


class Athletic():

  def __init__(self, builtinDataDir, serverCfg, encryptCfg, crawlerCfg):
    self.encryptTool = Encrypt(encryptCfg)
    self.crawlerCfg = crawlerCfg
    self.builtinDataDir = builtinDataDir
    self.dao = DAO(serverCfg.get('database'))
    self.db = AthleticDB(self.dao, self.builtinDataDir)
    # self.server = RESTServer(serverCfg.get('port'), self.dao, self.encryptTool)

  def start(self):
    self.db.initialize()
    locations = ['au:0', 'us:0', 'gb:0', 'sg:0']
    # locations = ['us:0', 'sg:0']
    keywords = [
        # {'specialist': 'yoga', 'keywords': ['yoga teacher', 'yoga instructor', 'yoga master']},
        # {'specialist': 'pilates', 'keywords': ['pilates teacher', 'pilates instructor', 'pilates master']},
        # {'specialist': 'MMA', 'keywords': ['mix martial art teacher', 'mix martial art instructor']},
        # {'specialist': 'dance', 'keywords': ['dance instructor', 'ballet teacher', 'ballet instructor', 'zumba instructor']}
        {'specialist': 'dance', 'keywords': ['ballet teacher', 'ballet instructor', 'zumba instructor']}
    ]
    auth = self.crawlerCfg.get('auth')
    methods = {
        'facebook': {'auth': fileUtils.readJson(auth.get('facebook'), self.builtinDataDir)},
        'google': {'auth': fileUtils.readJson(auth.get('google'), self.builtinDataDir)},
        'instagram': {'auth': fileUtils.readJson(auth.get('instagram'), self.builtinDataDir)},
        'linkedin': {'auth': fileUtils.readJson(auth.get('linkedin'), self.builtinDataDir)},
        'twitter': {'auth': fileUtils.readJson(auth.get('twitter'), self.builtinDataDir)},
        'website': {'auth': {}}
    }
    counter = {
        'total': 0,
        'start_page': 1,
        'expected_on_keyword_location': -1
    }
    counter['limited'] = counter.get('expected_on_keyword_location') != -1
    searchQuery = {
        'methods': dictUtils.extract(methods, ['linkedin']),
        'query': {
            'locations': locations,
            'keywords': keywords,
            'additional': {}
        },
        'counter': counter,
        'requestBy': 'zero',
    }
    specialists = ['yoga', 'pilates']

    queries = []
    for location in locations:
      # for specialist in specialists:
      query = dictUtils.deep_copy(searchQuery)
      query.get('query')['additional'] = {'location': {'$in': [location]}, 'specialist': {'$in': specialists}}
      queries.append(query)

    threads = []
    for query in queries:
      t = threading.Thread(target=self.runCrawler, args=(query,))
      threads.append(t)
      t.start()

  def runCrawler(self, query):
    crawlers = CrawlerFactory.parse(self.dao, query)
    CrawlerFactory.execute(CrawlerAction.COMPLETE, crawlers)

  def __export__(self):
    mapCol = {
        'fullName': {'index': 0, 'label': 'Full Name'},
        'title': {'index': 1, 'label': 'Title'},
        'address': {'index': 2, 'label': 'Address'},
        'linkedin': {'index': 3, 'label': 'Linkedin account'},
        'avatar': {'index': 4, 'label': 'Avatar'},
        'pdf': {'index': 5, 'label': 'PDF profile'},
    }
    handler = ExcelWriteHandler(mapCol=mapCol)
    data = self.dao.list('teachers', query={'specialist': 'pilates'}, fields=list(mapCol))
    handler.writeSheet(handler.addWorkSheet('Pilates'), rows=data)
    logger.info('Output file: {}'.format(handler.file))
