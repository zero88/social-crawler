import json
import logging
import urllib
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.support.ui import WebDriverWait

from ..exception import CrawlerError, LimitedError, NoResultError
from ..utils import fileUtils, textUtils
from .crawler import Crawler, CrawlerAction

logger = logging.getLogger(__name__)


class LinkedinCrawler(Crawler):

  def __init__(self, dao, searchQuery):
    super(LinkedinCrawler, self).__init__(dao, searchQuery)
    self.wait_page_load = 5
    self.ref_xpath = './/code[contains(., \'/voyager/api/search/cluster\')]'
    self.no_result_css_selector = '.search-no-results'
    self.config = {
        'url': 'https://www.linkedin.com',
        'profile': 'https://www.linkedin.com/in/{}',
        'search': {
            'people': 'https://www.linkedin.com/search/results/people/?facetGeoRegion={}&keywords={}&origin=FACETED_SEARCH&page={}'
        },
        'image': 'https://media.licdn.com/mpr/mpr{}'
    }

  def search0(self, runId):
    logger.info('Start searching on Linkedin')
    driver = webdriver.Chrome()
    try:
      self.__login__(driver)
      self.__search__(runId, driver)
    except Exception as e:
      logger.error('Unexpected', exc_info=True)
    finally:
      driver.close()
      driver.quit()

  def access0(self, runId):
    logger.info('Start access profile on Linkedin')
    pass

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

  def __search__(self, runId, driver):
    for searchKey in self.keywords:
      self.__searchBySpecialist__(runId, driver, searchKey.get('specialist'), searchKey.get('keywords'))
    self.completeTracking(runId)

  def __searchBySpecialist__(self, runId, driver, specialist, keywords):
    for keyword in keywords:
      self.__searchByLocation__(runId, driver, specialist, keyword)

  def __searchByLocation__(self, runId, driver, specialist, keyword):
    errors = []
    for location in self.locations:
      self.counter['count_on_keyword_location'] = 0
      self.counter['current_page'] = self.counter.get('start_page')
      while True:
        try:
          self.__searchPerPage__(driver, specialist, location, keyword)
        except (NoResultError, LimitedError) as err:
          self.stopTrack(runId, keyword, location, getattr(err, 'where', None), err.message)
          break
        except CrawlerError as ce:
          errors.append(ce)
          if len(errors) > 5:
            self.stopTrack(runId, keyword, location, '', ' - '.join(str(e.message) for e in errors))
            break
        finally:
          self.counter['current_page'] += 1

  def __searchPerPage__(self, driver, specialist, location, keyword):
    countPerPage = 0
    pageIndex = self.counter.get('current_page')
    searchURL = self.config.get('search').get('people').format(json.dumps([location]), urllib.quote(keyword), pageIndex)
    logger.info('Crawling in {}'.format(searchURL))
    driver.get(searchURL)
    driver.implicitly_wait(self.interval)
    self.__verifyHasMoreResult__(driver, searchURL)
    try:
      refElement = driver.find_element_by_xpath(self.ref_xpath)
      refData = json.loads(refElement.get_attribute('innerHTML'), encoding='utf-8')
      dataElement = driver.find_element_by_id(refData.get('body'))
      data = json.loads(dataElement.get_attribute('innerHTML'), encoding='utf-8')
      gap = self.counter.get('expected_on_keyword_location') - self.counter.get('count_on_keyword_location')
      limited = gap if self.counter.get('limited') is True else -1
      countPerPage = self.__analyze__(data, specialist, location, keyword, limited)
    except LimitedError as le:
      countPerPage = le.currentCount
      raise
    except (WebDriverException, Exception) as e:
      html = driver.page_source
      s = textUtils.optimizeText(specialist, '+')
      k = textUtils.optimizeText(keyword, '+')
      tmpFile = 'people_search_{}_{}_{}_{}.html'.format(location, s, k, pageIndex)
      tmp = fileUtils.writeTempFile(html, tmpFile)
      raise CrawlerError('Error parsing search page: "{}" - Error file: "{}"'.format(searchURL, tmp), e, logging.ERROR)
    finally:
      self.counter['count_on_keyword_location'] += countPerPage
      self.counter['total'] += countPerPage
      logger.info('Parsed {} profile(s) on l:{} - k:{} - p:{}'.format(countPerPage, location, keyword, pageIndex))

  def __verifyHasMoreResult__(self, driver, searchURL):
    try:
      driver.find_element_by_css_selector(self.no_result_css_selector)
      raise NoResultError('No results in {}'.format(searchURL), where=searchURL, level=logging.INFO)
    except WebDriverException as e:
      logger.debug(str(e))

  def __analyze__(self, data, specialist, location, keyword, limited):
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
      entity['key'] = key
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
      self.processEntity(entity, CrawlerAction.SEARCH)
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
