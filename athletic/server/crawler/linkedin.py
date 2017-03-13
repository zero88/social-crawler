import json
import logging
import re
import urllib
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.support.ui import WebDriverWait

import requests
from lxml import etree

from ..exception import CrawlerError, LimitedError, NoResultError
from ..utils import dictUtils, fileUtils, textUtils
from .crawler import Crawler, CrawlerAction, CrawlerState

logger = logging.getLogger(__name__)


class LinkedinCrawler(Crawler):

  def __init__(self, dao, searchQuery):
    super(LinkedinCrawler, self).__init__(dao, searchQuery)
    self.wait_page_load = 5
    self.config = {
        'url': 'https://www.linkedin.com',
        'profile': {
            'unavailable': '.profile-unavailable',
            'ref_xpath': './/code[contains(., \'/voyager/api/identity/profiles/{}/profileContactInfo\')]',
            'url': 'https://www.linkedin.com/in/{}'
        },
        'search': {
            'no_result_css_selector': '.search-no-results',
            'ref_xpath': './/code[contains(., \'/voyager/api/search/cluster\')]',
            'url': 'https://www.linkedin.com/search/results/people/?facetGeoRegion={}&keywords={}&origin=FACETED_SEARCH&page={}'
        },
        'image': 'https://media.licdn.com/mpr/mpr{}'
    }

  def search0(self, runId):
    logger.info('Start searching on Linkedin')
    result = {
        'total': 0,
        'stopAt': []
    }
    driver = webdriver.Chrome()
    try:
      self.__login__(driver)
      self.__search__(runId, driver, result)
    except Exception as e:
      logger.error('Unexpected', exc_info=True)
    finally:
      driver.close()
      driver.quit()
    return result

  # def access0(self, runId, record):
  #   logger.info('Start access profile on Linkedin')
  #   loginResponse = requests.request('POST', 'https://www.linkedin.com/uas/login-submit')
  #   print loginResponse.cookies
  #   print fileUtils.writeTempFile(text=loginResponse.cookies, filePath='cookies-tts.html')
  #   headers = {
  #       # 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.87 Safari/537.36',
  #       'User-Agent': 'Requests',
  #       # 'cache-control': 'no-cache',
  #       # 'postman-token': '65c70f41-0816-a021-a287-1a1a4bfe0462'
  #   }
  #   response = requests.request("GET", record.get('linkedin'), headers=headers,
  #                               allow_redirects=True)
  #   print response
  #   print response.headers
  #   # print fileUtils.writeTempFile(text=response.headers, filePath='headers-tts.html')
  #   print '=========================='
  #   print fileUtils.writeTempFile(text=response.text, filePath='content-tts.html')
  #   content = etree.fromstring(response.text)
  #   print '=========================='
  #   print content

  def access0(self, runId, records):
    logger.info('Start accessing on Linkedin')
    total, count, crawlerError, errors = 0, 0, 0, []
    if not records:
      return {'total': total, 'count': count, 'errors': errors}
    driver = webdriver.Chrome()
    try:
      self.__login__(driver)
      for record in records:
        total += 1
        key = urllib.quote_plus(textUtils.encode(record.get('key')))
        profileURL = textUtils.encode(record.get('linkedin'))
        logger.info('Crawling {} - URL: {}'.format('linkedin@' + key, profileURL))
        driver.get(profileURL)
        driver.implicitly_wait(self.interval)
        try:
          self.__ensurePageHasResult__(driver, self.config.get('profile').get('unavailable'))
          data = self.__extractData__(driver, self.config.get('profile').get('ref_xpath').format(key))
          logger.debug(
              'Method: {} - Key: {} - Data: {}'.format(self.searchQuery.get('method').get('type'), key, data))
          self.updateEntity(runId, record, self.__analyze_access__(data), CrawlerAction.ACCESS)
          count += 1
        except NoResultError as nre:
          errors.append({'key': key, 'url': nre.where, 'message': nre.message})
          self.updateEntity(runId, record, {'state': CrawlerState.ERROR}, CrawlerAction.ACCESS)
        except CrawlerError as ce:
          crawlerError += 1
          errors.append({'key': key, 'url': profileURL, 'message': ce.message})
          state = record.get('state')
          state = CrawlerState.ERROR if CrawlerState.SUSPICION == state else CrawlerState.SUSPICION
          self.updateEntity(runId, record, {'state': state}, CrawlerAction.ACCESS)
          if crawlerError > 100:
            break
    except Exception as e:
      logger.error('Unexpected', exc_info=True)
    finally:
      driver.close()
      driver.quit()
    return {'total': total, 'count': count, 'errors': errors}

  def complete0(self, runId):
    logger.info('Start complete profile on Linkedin')
    pass

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
      driver.implicitly_wait(self.wait_page_load)
    except WebDriverException as e:
      raise CrawlerError('Cannot login in linkedin', e, logging.ERROR)

  def __ensurePageHasResult__(self, driver, xpath):
    try:
      driver.find_element_by_css_selector(xpath)
      raise NoResultError('No results in {}'.format(driver.current_url), where=driver.current_url, level=logging.INFO)
    except WebDriverException as e:
      logger.debug(str(e))

  def __extractData__(self, driver, xpath):
    try:
      logger.debug('Parsing XPath {}'.format(xpath))
      refElement = driver.find_element_by_xpath(xpath)
      refData = json.loads(refElement.get_attribute('innerHTML'), encoding='utf-8')
      dataElement = driver.find_element_by_id(refData.get('body'))
      return json.loads(dataElement.get_attribute('innerHTML'), encoding='utf-8')
    except (WebDriverException, Exception) as e:
      html = driver.page_source
      tmp = fileUtils.writeTempFile(html, 'linkedin.html')
      raise CrawlerError('URL: {} - Error file: {}'.format(driver.current_url, tmp), e, logging.ERROR)

  def __analyze_access__(self, data):
    result = {
        'email': data.get('data').get('emailAddress'),
        'ims': [],
        'phones': [],
        'websites': [],
        'state': CrawlerState.OK
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
        url = self.parseWebsite(item.get('url'))
        website = url.get('website')
        if website is None:
          result = dictUtils.merge_dicts(False, result, url)
        else:
          result.get('websites').append(website)
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
      key = textUtils.encode(profile.get('publicIdentifier'))
      logger.info('Parsing data of profile: {}'.format(key))
      if textUtils.isEmpty(key) or key.upper() == 'UNKNOWN':
        continue
      entity = {}
      entity['key'] = textUtils.encode(key)
      entity['metadata'] = {'keywords': [keyword]}
      entity['firstName'] = textUtils.encode(profile.get('firstName'))
      entity['lastName'] = textUtils.encode(profile.get('lastName'))
      entity['specialist'] = specialist
      entity['location'] = location
      entity['title'] = textUtils.encode(profile.get('occupation'))
      entity['linkedin'] = self.config.get('profile').format(key)
      entity['avatar'] = self.__analyze_avatar__(people, profile) or ''
      search = self.__analyze_search__(people, profile)
      if search:
        entity['address'] = search.get('address')
        entity['pdf'] = self.__analyze_pdf__(people, search.get('action')) or ''
      self.processEntity(runId, entity, CrawlerAction.SEARCH)
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
