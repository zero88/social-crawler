import json
import logging
import urllib
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.support.ui import WebDriverWait

import requests
from lxml import etree
from requests.exceptions import HTTPError

from ..exception import CrawlerError, NoResultError
from ..utils import dictUtils, fileUtils, textUtils
from .crawler import Crawler

logger = logging.getLogger(__name__)


class WebsiteCrawler(Crawler):

  def __init__(self, dao, searchQuery):
    super(WebsiteCrawler, self).__init__(dao, searchQuery)
    self.wait_page_load = 5
    self.config = {
        'page': ['/contact', '/contact.html', '/contact-us', '/contact-us.html', '/connect', '/connect.html'],
        'search': {
            'email': 'mail|email|e:|m:'
            'phone': 'phone|telephone|tel|mobile|p:',
        },
    }

  def search0(self, runId):
    print 'Another Search'
    pass

  def access0(self, runId, records):
    print 'Another Access'
    driver = webdriver.Chrome()
    try:
      for record in records:
        total += 1
        key = record.get('key')
        method = record.get('metadata.method')
        websites = record.get('websites')
        logger.info('Crawling {}'.format(method + '@' + textUtils.encode(key)))
        if not websites:
          continue
        result = {
            'emails': [],
            'phones': [],
        }
        for website in websites:
          hasResult = False
          for page in self.config.get('page'):
            searchPage = website + page
            response = requests.request('GET', searchPage, allow_redirects=True)
            try:
              response.raise_for_status()
              driver.get(searchPage)
              driver.implicitly_wait(self.wait_page_load)
              result['emails'] = self.__analyze_email__(driver)
              result['phones'] = self.__analyze_phone__(driver)
              result = dictUtils.merge_dicts(result, self.__analyze_social_networks__(driver))
            except HTTPError as e:
              logger.debug(e)
              continue
    except Exception as e:
      logger.error('Unexpected', exc_info=True)
    finally:
      driver.close()
      driver.quit()
    return {'total': total, 'count': count, 'errors': errors}

  def complete0(self, runId):
    print 'Another Complete'
    pass

  def __analyze_email__(self, driver):
    emailEle = driver.find_element_by_xpath("//a[contains(concat(' ', @href, ' '), 'mailto:')]")
    return emailEle.text()

  def __analyze_phone__(self, driver):
    phoneEle = driver.find_element_by_xpath("//a[contains(concat(' ', @href, ' '), 'callto:')]")
    return phoneEle.text()

  def __analyze_social_networks__(self, driver):
    pass
