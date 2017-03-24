import json
from selenium import webdriver

from scrapy.crawler import CrawlerProcess
from scrapy.http import FormRequest, Request
# from scrapy.linkextractors.sgml import SgmlLinkExtractor
from scrapy.spiders import Rule
from scrapy.spiders.init import InitSpider

from utils import fileUtils


class ProductDetailsSpider(InitSpider):
  name = 'product_details_spider'
  allowed_domains = ['linkedin.com']
  login_page = 'https://www.linkedin.com/uas/login?fromSignIn=true&trk=uno-reg-join-sign-in'
  # login_page = 'http://www.linkedin.com'
  start_urls = ['https://www.linkedin.com']

  # rules = (
  #     Rule(SgmlLinkExtractor(allow=()),
  #          callback='parse_item',
  #          follow=True),
  # )

  def get_cookies(self):
    # driver = webdriver.Chrome(executable_path='C:/Tools/selenium/chromedriver.exe')
    driver = webdriver.Firefox(executable_path="C:/Tools/selenium/geckodriver.exe")
    base_url = 'https://www.linkedin.com/uas/login?fromSignIn=true&trk=uno-reg-join-sign-in'
    driver.get(base_url)
    driver.find_element_by_name("session_key").clear()
    driver.find_element_by_name("session_key").send_keys("lengocha.kin@gmail.com")
    driver.find_element_by_name("session_password").clear()
    driver.find_element_by_name("session_password").send_keys("Momomo1412")
    driver.find_element_by_name("signin").click()
    driver.implicitly_wait(30)
    cookies = driver.get_cookies()
    cookie_dic = {}
    for c in cookies:
      cookie_dic[c['name']] = c['value']
    driver.close()
    driver.quit()
    print fileUtils.writeTempFile(json.dumps(cookie_dic), filePath='cookie.json')
    return cookie_dic

  def init_request(self):
    print '=======================INIT======================='
    """This function is called before crawling starts."""
    return Request(url=self.login_page, callback=self.login)
    # cookies = self.get_cookies()
    # return Request(url='https://www.linkedin.com', cookies=cookies, callback=self.check_login_response)

  def login(self, response):
    print '=======================LOGIN======================='
    """Generate a login request."""
    return [FormRequest.from_response(response, formname='login_form',
                                      formdata={'session_key': 'lengocha.kin@gmail.com',
                                                'session_password': 'Momomo1412'},
                                      callback=self.login_cookies)]

  def login_cookies(self, response):
    print '=======================COOKIES======================='
    return Request(url='https://www.linkedin.com', cookies=self.get_cookies(), callback=self.check_login_response)

  def check_login_response(self, response):
    print '=======================CHECK LOGIN======================='
    """Check the response returned by a login request to see if we are
        successfully logged in.
        """
    print response
    print fileUtils.writeTempFile(response.body, filePath='content.html')
    print "==========================================="
    if "com.linkedin.voyager.identity.shared.MiniProfile" in response.body:
      print "=========Successfully logged in.========="
      return self.initialized()
      # Now the crawling can begin..
    else:
      print "==============Bad times :(==============="
      # Something went wrong, we couldn't log in, so nothing happens.

  def parse_item(self, response):
    print "==============PARSE ITEM=========================="
  # Scrape data from page

if __name__ == '__main__':
  process = CrawlerProcess({
      'USER_AGENT': 'Mozilla/5.0 (Windows NT x.y; Win64; x64; rv:10.0) Gecko/20100101 Firefox/10.0'
  })
  process.crawl(ProductDetailsSpider)
  process.start()
