import json
import logging
import urllib

import requests
from crawler import ZSCrawler

from ..exception import CrawlerError, NoResultError
from ..utils import fileUtils, textUtils

logger = logging.getLogger(__name__)


class GoogleCrawler(ZSCrawler):

    def __init__(self, dao, searchQuery):
        super(GoogleCrawler, self).__init__(dao, searchQuery)

    def search0(self, runId):
        print('G Search')
        pass

    def access0(self, runId):
        print('G Access')

    def complete0(self, runId):
        print('G Complete')
