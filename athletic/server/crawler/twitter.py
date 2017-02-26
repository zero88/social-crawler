import json
import logging
import urllib

import requests
from crawler import Crawler

from ..exception import CrawlerError, NoResultError
from ..utils import fileUtils, textUtils

logger = logging.getLogger(__name__)


class TwitterCrawler(Crawler):

  def __init__(self, dao, searchQuery):
    super(TwitterCrawler, self).__init__(dao, searchQuery)

  def search0(self, runId):
    print 'twitter Search'
    pass

  def access0(self, runId):
    print 'twitter Access'
    pass

  def complete0(self, runId):
    print 'twitter Complete'
    pass
