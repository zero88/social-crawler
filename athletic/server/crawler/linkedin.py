#!/usr/bin/python
# encoding=utf8
import json
import logging
import re
import urllib
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.support.ui import WebDriverWait

import requests
from lxml import etree
from scrapy.crawler import CrawlerProcess, CrawlerRunner
from scrapy.utils.log import configure_logging
from twisted.internet import defer, reactor

from spiderman import Spiderman

from ..exception import CrawlerError, LimitedError, NoResultError
from ..utils import dictUtils, fileUtils, textUtils
from .crawler import Crawler, CrawlerAction, CrawlerBrowser, CrawlerState

logger = logging.getLogger(__name__)


class LinkedinCrawler(Crawler):

  def __init__(self, dao, searchQuery):
    super(LinkedinCrawler, self).__init__(dao, searchQuery)
    self.delay = 5
    self.config = {
        'url': 'https://www.linkedin.com',
        'login': {
            'url': 'https://www.linkedin.com/uas/login?fromSignIn=true&trk=uno-reg-join-sign-in',
            'formName': 'login',
            'submitName': 'signin',
            'successItem': 'com.linkedin.voyager.identity.shared.MiniProfile'
        },
        'profile': {
            'unavailable': '.profile-unavailable',
            'ref_xpath': './/code[contains(., "/profileContactInfo")]/text()',
            'url': 'https://www.linkedin.com/in/{}'
        },
        'search': {
            'no_result_css_selector': '.search-no-results',
            'ref_xpath': './/code[contains(., \'/voyager/api/search/cluster\')]',
            'url': 'https://www.linkedin.com/search/results/people/?facetGeoRegion={}&keywords={}&origin=FACETED_SEARCH&page={}'
        },
        'image': 'https://media.licdn.com/mpr/mpr{}'
    }
    self.config['auth'] = {'session_key': self.account, 'session_password': self.password}

  def search0(self, runId):
    logger.info('Start searching on Linkedin')
    result = {
        'total': 0,
        'stopAt': []
    }
    driver = webdriver.PhantomJS(
        executable_path='C:/Users/sontt/Projects/work/startl.us/athletic-teacher/athletic/exec/phantomjs.exe')
    try:
      self.__login__(driver)
      self.__search__(runId, driver, result)
    except Exception as e:
      logger.error('Unexpected', exc_info=True)
    finally:
      driver.close()
      driver.quit()
    return result

  @defer.inlineCallbacks
  def crawl(self, runner, runId, records):
    yield runner.crawl(Spiderman, runId=runId, pipeline=self, items=records, siteCfg=self.config)
    reactor.stop()

  def access0(self, runId, records):
    logger.info('Start accessing on Linkedin')
    # runner = CrawlerRunner({
    #     'USER_AGENT': CrawlerBrowser.get_useragent(CrawlerBrowser.FIREFOX),
    #     'DOWNLOAD_DELAY': 1
    # })
    # self.crawl(runner, runId, records)
    # # d = runner.crawl(Spiderman, runId=runId, pipeline=self, items=records, siteCfg=self.config)
    # # d.addBoth(lambda _: reactor.stop())
    # reactor.run()
    configure_logging(install_root_handler=False)
    process = CrawlerProcess({
        'USER_AGENT': CrawlerBrowser.get_useragent(CrawlerBrowser.EDGE),
        'DOWNLOAD_DELAY': 1
    })
    process.crawl(Spiderman, runId=runId, pipeline=self, items=records,
                  browser=CrawlerBrowser.EDGE, siteCfg=self.config)
    process.start()

  def analyzeData(self, runId, item, response):
    data = self.__extractData__(response, self.config.get('profile').get('ref_xpath'))
    logger.debug(u'Method: {} - Key: {} - Data: {}'.format('access', item.get('key'), data))
    entity = self.__analyze_access__(data)
    logger.info(fileUtils.writeTempFile(response.body.decode('utf-8'), filePath=fileUtils.joinPaths('athletic', 'linkedin',
                                                                                                    'access', 'profile.html')))
    self.updateEntity(runId, item, entity=entity, action=CrawlerAction.ACCESS)

  def notifyError(self, runId, item, response):
    self.updateRecordState(runId, item, CrawlerState.ERROR, CrawlerAction.ACCESS)

  def __login__(self, driver):
    try:
      logger.info('Login in {}'.format(self.config.get('url')))
      driver.get(self.config.get('url'))
      userfield = driver.find_element_by_id('login-email')
      passfield = driver.find_element_by_id('login-password')
      submit_form = driver.find_element_by_class_name('login-form')
      if userfield and passfield:
        userfield.send_keys(self.account)
        passfield.send_keys(self.password)
        submit_form.submit()
      driver.implicitly_wait(self.delay)
    except WebDriverException as e:
      raise CrawlerError('Cannot login in linkedin', e, logging.ERROR)

  def __ensurePageHasResult__(self, driver, xpath):
    try:
      driver.find_element_by_css_selector(xpath)
      raise NoResultError('No results in {}'.format(driver.current_url), where=driver.current_url, level=logging.INFO)
    except WebDriverException as e:
      logger.debug(str(e))

  def __extractData__(self, response, xpath):
    try:
      logger.debug('Parsing XPath {}'.format(xpath))
      refElement = response.selector.xpath(xpath).extract_first()
      print refElement
      if refElement is None:
        raise CrawlerError('Not found {}'.format(xpath))
      refData = json.loads(textUtils.encode(refElement), encoding='utf-8')
      if refData.get('status') != 200:
        raise CrawlerError('Value is forbidden ??')
      data = response.selector.xpath('//*[@id=$val]/text()', val=refData.get('body')).extract_first()
      return json.loads(textUtils.encode(data), encoding='utf-8')
    except Exception as e:
      html = response.body.decode('utf-8')
      tmp = fileUtils.writeTempFile(html, fileUtils.joinPaths('athletic', 'linkedin', 'access', 'error-profile.html'))
      raise CrawlerError('URL: {} - Error file: {}'.format(response.url, tmp), e, logging.ERROR)
    # try:
    #   logger.debug('Parsing XPath {}'.format(xpath))
    #   refElement = driver.find_element_by_xpath(xpath)
    #   refData = json.loads(refElement.get_attribute('innerHTML'), encoding='utf-8')
    #   dataElement = driver.find_element_by_id(refData.get('body'))
    #   return json.loads(dataElement.get_attribute('innerHTML'), encoding='utf-8')
    # except (WebDriverException, Exception) as e:
    #   html = driver.page_source
    #   tmp = fileUtils.writeTempFile(html, fileUtils.joinPaths(self.tempPrefix, 'linkedin.html'))
    #   raise CrawlerError('URL: {} - Error file: {}'.format(driver.current_url, tmp), e, logging.ERROR)

  def __analyze_access__(self, data):
    result = {
        'email': data.get('data').get('emailAddress'),
        'im': [],
        'phone': [],
        'website': []
    }
    included = data.get('included')
    for item in included:
      itemType = item.get('$type')
      if itemType == 'com.linkedin.voyager.identity.profile.IM':
        result.get('ims').append(dictUtils.extract(item, keys=['provider', 'id']))
      elif itemType == 'com.linkedin.voyager.identity.profile.PhoneNumber':
        result.get('phones').append(dictUtils.extract(item, keys=['type', 'number']))
      elif itemType == 'com.linkedin.voyager.identity.shared.TwitterHandle':
        result['twitter'] = 'https://twitter.com/' + item.get('name')
      elif itemType == 'com.linkedin.voyager.identity.profile.ProfileWebsite':
        url = self.detectWebsiteType(item.get('url'))
        website = url.get('website')
        if website is None:
          result = dictUtils.merge_dicts(False, result, url)
        else:
          result.get('website').append(website)
    return result

  def __search__(self, runId, driver, result):
    for searchKey in self.keywords:
      self.__searchBySpecialist__(runId, driver, result, searchKey.get('specialist'), searchKey.get('keywords'))

  def __searchBySpecialist__(self, runId, driver, result, specialist, keywords):
    for keyword in keywords:
      self.__searchByLocation__(runId, driver, result, specialist, keyword)

  def __searchByLocation__(self, runId, driver, result, specialist, keyword):
    for location in self.locations:
      errors = []
      stop = {
          'keyword': keyword,
          'location': location,
          'count': 0,
          'start_page': self.counter.get('start_page'),
          'current_page': self.counter.get('start_page')
      }
      while True:
        pageIndex = stop.get('current_page')
        gap = self.counter.get('expected_on_keyword_location') - stop.get('count')
        limited = gap if self.counter.get('limited') is True else -1
        try:
          stop['count'] += self.__searchPerPage__(runId, driver, specialist, location,
                                                  keyword, pageIndex, limited)
        except LimitedError as le:
          stop['count'] += le.currentCount
          stop['message'] = le.message
        except NoResultError as nre:
          stop['url'] = nre.where
          stop['message'] = nre.message
          break
        except CrawlerError as ce:
          errors.append(ce)
          if len(errors) > 5:
            stop['message'] = ' - '.join(str(e.message) for e in errors)
            stop['url'] = nre.where
            break
        finally:
          logger.info('Parsed {} profile(s) on l:{} - k:{} - p:{}'.format(stop.get('count'),
                                                                          location, keyword, pageIndex))
          stop['current_page'] += 1
          result['total'] += stop.get('count')
      result.get('stopAt').append(stop)

  def __searchPerPage__(self, runId, driver, specialist, location, keyword, pageIndex, limited):
    searchURL = self.config.get('search').get('url').format(json.dumps([location]), urllib.quote(keyword), pageIndex)
    logger.info('Crawling in {}'.format(searchURL))
    driver.get(searchURL)
    driver.implicitly_wait(self.interval)
    self.__ensurePageHasResult__(driver, self.config.get('search').get('no_result_css_selector'))
    data = self.__extractData__(driver, self.config.get('search').get('ref_xpath'))
    return self.__analyze__(runId, data, specialist, location, keyword, limited)

  def __analyze__(self, runId, data, specialist, location, keyword, limited):
    people = data.get('included')
    if people is None:
      raise NoResultError('No people in {}'.format(json.dumps(data)), level=logging.ERROR)
    miniProfiles = [p for p in people if p.get('$type') == 'com.linkedin.voyager.identity.shared.MiniProfile']
    countPerPage = 0
    for profile in miniProfiles:
      if limited >= 0 and countPerPage >= limited:
        raise LimitedError('Searching limited: {}'.format(limited), currentCount=countPerPage)
      key = profile.get('publicIdentifier')
      logger.info(u'Parsing data of profile: {}'.format(key))
      if textUtils.isEmpty(key) or key.upper() == 'UNKNOWN':
        continue
      entity = {}
      entity['key'] = textUtils.decode(key)
      entity['metadata'] = {'keywords': [keyword]}
      entity['firstName'] = textUtils.decode(profile.get('firstName'))
      entity['lastName'] = textUtils.decode(profile.get('lastName'))
      entity['specialist'] = specialist
      entity['location'] = location
      entity['title'] = textUtils.decode(profile.get('occupation'))
      entity['linkedin'] = self.config.get('profile').format(key)
      entity['avatar'] = self.__analyze_avatar__(people, profile) or ''
      search = self.__analyze_search__(people, profile)
      if search:
        entity['address'] = search.get('address')
        entity['pdf'] = self.__analyze_pdf__(people, search.get('action')) or ''
      self.processEntity(runId, entity)
      countPerPage += 1
    return countPerPage

  def __analyze_search__(self, people, profile):
    searchProfileType = 'com.linkedin.voyager.search.SearchProfile'
    objectUrn = profile.get('objectUrn')
    if objectUrn:
      logger.debug('Analyze search: {}'.format(objectUrn))
      search = [p for p in people if p.get('$type') == searchProfileType and p.get('backendUrn') == objectUrn]
      if search:
        return {
            'address': textUtils.encode(search[0].get('location')),
            'action': textUtils.encode(search[0].get('profileActions'))
        }
    return None

  def __analyze_avatar__(self, people, profile):
    mediaType = 'com.linkedin.voyager.common.MediaProcessorImage'
    if profile.get('picture'):
      imageId = profile.get('picture').get(mediaType)
      logger.debug('Analyze avatar: {}'.format(imageId))
      image = [p for p in people if p.get('$type') == mediaType and p.get('$id') == imageId]
      if image:
        return self.config.get('image').format(textUtils.encode(image[0].get('id')))
    return None

  def __analyze_pdf__(self, people, action):
    pdfType = 'com.linkedin.voyager.identity.profile.actions.SaveToPdf'
    logger.debug('Analyze pdf: {}'.format(action))
    pdf = [p for p in people if p.get('$type') == pdfType and action in p.get('$id')]
    if pdf:
      return textUtils.encode(pdf[0].get('requestUrl'))
    return None
