import json
import logging

from scrapy.http import FormRequest, Request
from scrapy.spiders.init import InitSpider

from ..exception import CrawlerError, LimitedError, NoResultError
from ..utils import dictUtils, fileUtils, textUtils
from .crawler import CrawlerBrowser

logger = logging.getLogger(__name__)


class Spiderman(InitSpider):

  def __init__(self, runId, pipeline, name='spiderman', browser=CrawlerBrowser.FIREFOX, items=[], siteCfg={}, *args, **kwargs):
    super(Spiderman, self).__init__(name=name, *args, **kwargs)
    self.runId = runId
    self.pipeline = pipeline
    self.browser = browser
    self.items = items
    self.siteCfg = siteCfg
    self.loginCfg = siteCfg.get('login')
    self.errors = []
    self.count = 0

  def init_request(self):
    print '=======================INIT======================='
    """This function is called before crawling starts."""
    return Request(url=self.loginCfg.get('url'), callback=self.__login__)

  def initialized(self):
    for item in self.items:
      # TODO FIX IT 'linkedin'
      request = Request(item.get('linkedin'), self.parse)
      request.meta['item'] = item
      yield request

  def parse(self, response):
    print "Existing settings: %s" % self.settings.attributes.get('USER_AGENT')
    print '=======================PARSE ITEM=========================='
    item = response.meta.get('item')
    try:
      if response.status != 200:
        # self.pipeline.handleNoResult(NoResultError('No results in {}'.format(response.url), where=response.url))
        raise NoResultError('No results {}::{}'.format(item.get('key'), response.url), where=response.url)
      self.pipeline.analyzeData(self.runId, item, response)
      self.count += 1
    except (NoResultError, CrawlerError) as nre:
      print item
      self.errors.append({'key': item.get('key'), 'url': response.url, 'message': nre.message})
      self.pipeline.notifyError(self.runId, item, response)

  def closed(self, reason):
    self.pipeline.finish(self.runId, {'total': len(self.items), 'count': self.count, 'errors': self.errors})

  def __login__(self, response):
    print '=======================LOGIN======================='
    """Generate a login request."""
    return [FormRequest.from_response(response, callback=self.__login_cookies__,
                                      formname=self.loginCfg.get('formName'),
                                      formdata=self.siteCfg.get('auth'))]

  def __login_cookies__(self, response):
    print '=======================COOKIES======================='
    return Request(url=self.siteCfg.get('url'), cookies=self.__get_cookies__(), callback=self.__check_login_response__)

  def __get_cookies__(self):
    driver = CrawlerBrowser.get_driver(self.browser)
    driver.get(self.loginCfg.get('url'))
    for key, value in self.siteCfg.get('auth').items():
      driver.find_element_by_name(key).send_keys(value)
    driver.find_element_by_name(self.loginCfg.get('submitName')).click()
    driver.implicitly_wait(30)
    cookies = driver.get_cookies()
    cookie_dic = {}
    for c in cookies:
      cookie_dic[c['name']] = c['value']
    driver.close()
    driver.quit()
    # print fileUtils.writeTempFile(json.dumps(cookie_dic), filePath='cookie.json')
    return cookie_dic

  def __check_login_response__(self, response):
    print '=======================CHECK LOGIN======================='
    """Check the response returned by a login request to see if we are
        successfully logged in.
        """
    if self.loginCfg.get('successItem') in response.body:
      print "=========Successfully logged in.========="
      return self.initialized()
      # Now the crawling can begin..
    else:
      print "==============Bad times :(==============="
      # Something went wrong, we couldn't log in, so nothing happens.
