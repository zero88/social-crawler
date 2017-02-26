import logging

from crawler.crawler import Crawler, CrawlerAction
from crawler.factory import CrawlerFactory
from crawler.linkedin import LinkedinCrawler

from db import DAO, AthleticDB
from encrypt import Encrypt
from utils import fileUtils

# from server import RESTServer

logger = logging.getLogger(__name__)


class Athletic():

  def __init__(self, datafile, serverCfg, encryptCfg, crawlerCfg):
    self.encryptTool = Encrypt(encryptCfg)
    self.crawlerCfg = crawlerCfg
    self.datafile = datafile
    self.dao = DAO(serverCfg.get('database'))
    self.db = AthleticDB(self.dao, self.datafile)
    # self.server = RESTServer(serverCfg.get('port'), self.dao, self.encryptTool)

  def start(self):
    self.db.initialize()
    locations = ['sg:0', 'au:0', 'us:0', 'gb:0']
    keywords = [
        # {'specialist': 'yoga', 'keywords': ['yoga teacher', 'yoga instructor', 'yoga master']},
        {'specialist': 'yoga', 'keywords': ['yoga instructor', 'yoga master']},
        {'specialist': 'pilates', 'keywords': ['pilates teacher', 'pilates instructor', 'pilates master']},
        # {'specialist': 'MMA', 'keywords': ['mix martial art teacher', 'mix martial art instructor']},
        # {'specialist': 'dance', 'keywords': []},
    ]
    auth = self.crawlerCfg.get('auth')
    searchQuery = {
        'methods': {
            'facebook': {'auth': fileUtils.readJson(auth.get('facebook'), self.datafile)},
            'google': {'auth': fileUtils.readJson(auth.get('google'), self.datafile)},
            'instagram': {'auth': fileUtils.readJson(auth.get('instagram'), self.datafile)},
            'linkedin': {'auth': fileUtils.readJson(auth.get('linkedin'), self.datafile)},
            'twitter': {'auth': fileUtils.readJson(auth.get('twitter'), self.datafile)},
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
