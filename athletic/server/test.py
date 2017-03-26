import json
import logging
from selenium import webdriver

from scrapy.crawler import CrawlerProcess
from scrapy.http import FormRequest, Request
from scrapy.selector import Selector
from scrapy.spiders import Rule
from scrapy.spiders.init import InitSpider

from exception import CrawlerError, LimitedError, NoResultError
from utils import dictUtils, fileUtils, textUtils

logger = logging.getLogger(__name__)


class Spiderman(InitSpider):

  # custom_settings = {
  #     'USER_AGENT': 'Mozilla/5.0 (Windows NT x.y; Win64; x64; rv:10.0) Gecko/20100101 Firefox/10.0'
  # }

  def __init__(self, name='spiderman', records=[], site={}, *args, **kwargs):
    super(Spiderman, self).__init__(name=name, *args, **kwargs)
    self.records = records
    self.site = site
    self.loginCfg = site.get('login')
    self.config = {
        'url': 'https://www.linkedin.com',
        'profile': {
            'unavailable': '.profile-unavailable',
            # 'ref_xpath': './/code[contains(., \'/voyager/api/identity/profiles/{}/profileContactInfo\')]',
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
    self.socialRegex = {
        'email': r'[a-z][a-z0-9_\-\.]+@([a-z0-9\-]+\.)+[a-z]{2,4}',
        'facebook': r'(https?://)?(www\.)?(mbasic.facebook|m\.facebook|facebook|fb)\.(com|me)/(?:(?:\w\.)*#!\/)?(?:pages\/)?(?:[\w\-\.]+\/)*([\w\-\.]+)',
        'flickr': r'(https?://)?(www\.)?flickr\.com/([\w\-\.]+)',
        'github': r'(https?://)?(www\.)?github\.com/([\w\-\.]+)',
        'gplus': r'(https?://)?plus\.google\.com/([\w\-\.]+)',
        'instagram': r'(https?://)?(www\.)?(instagram.com|instagr.am)/([a-z0-9_\-]{2,})/?',
        'linkedin': r'(https?://)?(www\.)?linkedin\.com/in/[a-z0-9_\-]+\/?',
        'pinterest': r'(https?://)?(www\.)?pinterest\.com/([\w\-\.]+)',
        'twitter': r'(https?://)?twitter\.com\/(?:(#!\/)?(?:[\w\-\.]+\/)*([\w\-\.]+))',
        'youtube': r'(https?://)?(www\.)?youtube\.com/(channel\/|user\/)?[a-zA-Z0-9\-]+',
        'phone': {
            'prefix': r'(telephone|phone|mobile|tel|call|call us)(\s?:|\s?-)?(?i)',
            'regex': r'^(?:(?:\(?(?:00|\+)([1-4]\d\d|[1-9]\d?)\)?)?[\-\.\s\\\/]?)?((?:\(?\d{1,}\)?[\-\.\ \\\/]?){0,})(?:[\-\.\ \\\/]?(?:#|ext\.?|extension|x)[\-\.\ \\\/]?(\d+))?$(?i)'
        }
    }
    self.errors = []

  def init_request(self):
    print '=======================INIT======================='
    """This function is called before crawling starts."""
    return Request(url=self.loginCfg.get('url'), callback=self.__login__)

  def initialized(self):
    for record in self.records:
      request = Request(record.get('url'), self.parse)
      request.meta['record'] = record
      yield request

  def parse(self, response):
    print("Existing settings: %s" % self.settings.attributes.get('USER_AGENT'))
    print '=======================PARSE ITEM=========================='
    record = response.meta.get('record')
    print record
    print '=======================PARSE PROFILE=========================='
    try:
      if response.status != 200:
        raise NoResultError('No results in {}'.format(response.url), where=response.url, level=logging.INFO)
      data = self.__extractData__(response, self.config.get('profile').get('ref_xpath'))
      logger.debug(u'Method: {} - Key: {} - Data: {}'.format('access', record.get('key'), data))
      # self.updateEntity(runId, record, entity=self.__analyze_access__(data), action=CrawlerAction.ACCESS)
      logger.info(self.__analyze_access__(data))
      print fileUtils.writeTempFile(response.body, filePath=fileUtils.joinPaths('athletic', 'linkedin',
                                                                                'access', 'profile.html'))
      # count += 1
    except NoResultError as nre:
      self.errors.append({'key': record.get('key'), 'url': nre.where, 'message': nre.message})
      # self.updateRecordState(runId, record, CrawlerState.ERROR, CrawlerAction.ACCESS)
    except CrawlerError as ce:
      # crawlerError += 1
      self.errors.append({'key': key, 'url': response.url, 'message': ce.message})
      # self.updateRecordState(runId, record, action=CrawlerAction.ACCESS)
      # if crawlerError > 20:
      #   break

  def __extractData__(self, response, xpath):
    try:
      logger.debug('Parsing XPath {}'.format(xpath))
      selector = Selector(response=response)
      refElement = selector.xpath(xpath).extract_first()
      print refElement
      if refElement is None:
        raise CrawlerError('Not found {}'.format(xpath))
      refData = json.loads(textUtils.encode(refElement), encoding='utf-8')
      data = selector.xpath('//*[@id=$val]/text()', val=refData.get('body')).extract_first()
      return json.loads(textUtils.encode(data), encoding='utf-8')
    except Exception as e:
      html = response.body
      tmp = fileUtils.writeTempFile(html, fileUtils.joinPaths('athletic', 'linkedin', 'access', 'error-profile.html'))
      raise CrawlerError('URL: {} - Error file: {}'.format(response.url, tmp), e, logging.ERROR)

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

  def detectWebsiteType(self, url):
    for key, regex in self.socialRegex.iteritems():
      if key == 'phone':
        continue
      if textUtils.match(url, regex):
        return {key: url}
    return {'website': url}

  def __login__(self, response):
    print '=======================LOGIN======================='
    """Generate a login request."""
    return [FormRequest.from_response(response, callback=self.__login_cookies__,
                                      formname=self.loginCfg.get('formName'),
                                      formdata=self.loginCfg.get('auth'))]

  def __login_cookies__(self, response):
    print '=======================COOKIES======================='
    return Request(url=self.site.get('baseURL'), cookies=self.__get_cookies__(), callback=self.__check_login_response__)

  def __get_cookies__(self):
    # driver = webdriver.Chrome(executable_path='C:/Tools/selenium/chromedriver.exe')
    driver = webdriver.Firefox(
        executable_path="C:/Users/sontt/Projects/work/startl.us/athletic-teacher/athletic/exec/geckodriver.exe")
    driver.get(self.loginCfg.get('url'))
    for key, value in self.loginCfg.get('auth').items():
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
    if "com.linkedin.voyager.identity.shared.MiniProfile" in response.body:
      print "=========Successfully logged in.========="
      return self.initialized()
      # Now the crawling can begin..
    else:
      print "==============Bad times :(==============="
      # Something went wrong, we couldn't log in, so nothing happens.

if __name__ == '__main__':
  site = {
      'baseURL': 'https://www.linkedin.com',
      'login': {
          'url': 'https://www.linkedin.com/uas/login?fromSignIn=true&trk=uno-reg-join-sign-in',
          'formName': 'login',
          'submitName': 'signin',
          'auth': {
              'session_key': 'lengocha.kin@gmail.com',
              'session_password': 'Momomo1412'
          }
      }
  }
  records = [
      {'url': 'https://www.linkedin.com/in/kandace-gaudette-42a38ba5', 'key': 'kandace-gaudette-42a38ba5'},
      # {'url': 'https://www.linkedin.com/in/cara-schroter-0aa22288', 'key': 'cara-schroter-0aa22288'}
  ]
  process = CrawlerProcess({
      'USER_AGENT': 'Mozilla/5.0 (Windows NT x.y; Win64; x64; rv:10.0) Gecko/20100101 Firefox/10.0'
  })
  process.crawl(Spiderman, site=site, records=records)
  process.start()
