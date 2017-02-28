import logging

from crawler.crawler import CrawlerAction
from crawler.factory import CrawlerFactory

from db import DAO, AthleticDB
from encrypt import Encrypt
from excel import ExcelWriteHandler
from utils import fileUtils

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
    locations = ['us:0', 'au:0', 'gb:0', 'sg:0']
    # locations = ['us:0', 'gb:0']
    keywords = [
        # {'specialist': 'yoga', 'keywords': ['yoga teacher', 'yoga instructor', 'yoga master']},
        {'specialist': 'pilates', 'keywords': ['pilates teacher', 'pilates instructor', 'pilates master']},
        # {'specialist': 'MMA', 'keywords': ['mix martial art teacher', 'mix martial art instructor']},
        # {'specialist': 'dance', 'keywords': []},
    ]
    auth = self.crawlerCfg.get('auth')
    searchQuery = {
        'methods': {
            'facebook': {'auth': fileUtils.readJson(auth.get('facebook'), self.builtinDataDir)},
            'google': {'auth': fileUtils.readJson(auth.get('google'), self.builtinDataDir)},
            'instagram': {'auth': fileUtils.readJson(auth.get('instagram'), self.builtinDataDir)},
            'linkedin': {'auth': fileUtils.readJson(auth.get('linkedin'), self.builtinDataDir)},
            'twitter': {'auth': fileUtils.readJson(auth.get('twitter'), self.builtinDataDir)},
            'other': {'auth': {}}
        },
        'query': {
            'locations': locations,
            'keywords': keywords,
            'total': -1
        },
        'requestBy': 'zero',
    }
    crawlers = CrawlerFactory.parse(self.dao, searchQuery)
    CrawlerFactory.execute(CrawlerAction.SEARCH, crawlers)

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
