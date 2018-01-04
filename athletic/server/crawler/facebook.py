#!/usr/bin/python
# encoding=utf8
import json
import logging
import urllib

import requests
from crawler import ZSCrawler

from ..exception import CrawlerError, NoResultError
from ..utils import fileUtils, textUtils

logger = logging.getLogger(__name__)


class FacebookCrawler(ZSCrawler):

    def __init__(self, dao, searchQuery):
        super(FacebookCrawler, self).__init__(dao, searchQuery)

    def search0(self, runId):
        print('Fb Search')

    def access0(self, runId):
        print('Fb Access')

    def complete0(self, runId):
        print('Fb Complete')
