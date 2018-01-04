import logging
import threading

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.schedulers.blocking import BlockingScheduler
from crawler.crawler import CrawlerAction
from crawler.crawlerQuery import QueryBuilder
from crawler.factory import CrawlerFactory

from db import DAO, CrawlerDB
from encrypt import Encrypt
from excel import ExcelWriteHandler
from utils import dictUtils, fileUtils

# from server import RESTServer

logger = logging.getLogger(__name__)


class ZSCApp():

    def __init__(self, builtinDataDir, serverCfg, encryptCfg, crawlerCfg):
        self.encryptTool = Encrypt(encryptCfg)
        self.dao = DAO(serverCfg.get('database'))
        self.db = CrawlerDB(self.dao, builtinDataDir)
        self.crawlerQueryBuilder = self.__initialize_crawler__(builtinDataDir, crawlerCfg)
        self.worker = BlockingScheduler()
        # self.server = RESTServer(serverCfg.get('port'), self.dao, self.encryptTool)

    def __initialize_crawler__(self, builtinDataDir, crawlerCfg):
        auth = crawlerCfg.get('auth')
        builtinMethods = {
            'facebook': {'auth': fileUtils.readJson(auth.get('facebook'), builtinDataDir)},
            'google': {'auth': fileUtils.readJson(auth.get('google'), builtinDataDir)},
            'instagram': {'auth': fileUtils.readJson(auth.get('instagram'), builtinDataDir)},
            'linkedin': {'auth': fileUtils.readJson(auth.get('linkedin'), builtinDataDir)},
            'twitter': {'auth': fileUtils.readJson(auth.get('twitter'), builtinDataDir)},
            'website': {'auth': []}
        }
        return QueryBuilder(methods=builtinMethods)

    def start(self):
        self.db.initialize()
        # self.__add_job(self.__access__, name='ACCESS', interval=30)
        # self.__add_job(self.__complete__, name='COMPLETE')
        # self.worker.start()
        # self.__search__(filterMethods=['linkedin'])
        # self.__access__(filterMethods=['linkedin'])
        self.__complete__(filterMethods=['linkedin', 'instagram'])
        # self.__export__()

    def __add_job(self, func, name='ACCESS', interval=1):
        jobId = 'jobID::' + name
        self.worker.add_job(func, id=jobId, trigger='interval', seconds=interval, max_instances=1)

    def __search__(self, filterMethods=[], filterSpecs=[]):
        queries = self.crawlerQueryBuilder.build('zero', filterMethods=filterMethods, filterSpecs=filterSpecs)
        crawlers = CrawlerFactory.parse(self.dao, queries)
        CrawlerFactory.execute(CrawlerAction.SEARCH, crawlers)

    def __access__(self, filterMethods=[], filterSpecs=[]):
        queries = self.crawlerQueryBuilder.build('zero', filterMethods=filterMethods, filterSpecs=filterSpecs)
        crawlers = CrawlerFactory.parse(self.dao, queries)
        CrawlerFactory.execute(CrawlerAction.ACCESS, crawlers)

    def __complete__(self, filterMethods=[], filterSpecs=[]):
        queries = self.crawlerQueryBuilder.build('zero', filterMethods=filterMethods, filterSpecs=filterSpecs)
        crawlers = CrawlerFactory.parse(self.dao, queries)
        CrawlerFactory.execute(CrawlerAction.COMPLETE, crawlers)
        threads = []
        for crawler in crawlers:
            t = threading.Thread(target=CrawlerFactory.execute, args=(CrawlerAction.COMPLETE, [crawler]))
            threads.append(t)
            t.start()

    def __export__(self):
        mapCol = {
            'fullName': {'index': 0, 'label': 'Full Name'},
            'title': {'index': 1, 'label': 'Title'},
            'address': {'index': 2, 'label': 'Address'},
            'linkedin': {'index': 3, 'label': 'Linkedin account'},
            'avatar': {'index': 4, 'label': 'Avatar'},
            'pdf': {'index': 5, 'label': 'PDF profile'},
            'socials.twitter':  {'index': 6, 'label': 'Social.Twitter'},
        }
        handler = ExcelWriteHandler(file="teachers.xlsx", mapCol=mapCol)
        data = self.dao.list('teachers', query={'specialist': 'pilates'}, fields=list(mapCol), limit=10)
        handler.writeSheet(handler.addWorkSheet('Pilates'), rows=data)
        logger.info('Output file: {}'.format(handler.file))
