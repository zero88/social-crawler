#!/usr/bin/python
# encoding=utf8
import logging

from lxml import etree
from lxml.etree import ParseError

from ..exception import CrawlerError, NoResultError
from ..utils import dictUtils, fileUtils, textUtils
from .crawler import Crawler, CrawlerAction, CrawlerState

logger = logging.getLogger(__name__)


class WebsiteCrawler(Crawler):

  def __init__(self, dao, searchQuery):
    super(WebsiteCrawler, self).__init__(dao, searchQuery)
    self.config = {
        'page': [
            '/contact', '/contact-us', '/about', '/connect',
            '/contact.html', '/contact-us.html', '/about.html', '/connect.html'
        ]
    }

  def search0(self, runId):
    print 'Another Search'
    pass

  def access0(self, runId, records):
    total, count, errors = 0, 0, []
    try:
      for record in records:
        total += 1
        key = record.get('key')
        method = record.get('metadata').get('method')
        websites = record.get('website')
        logger.info(u'Crawling {}@{}'.format(method, key))
        if not websites:
          continue
        result = {}
        for website in websites:
          try:
            logger.info(u'Crawling data - website::{}'.format(website))
            websiteResult, websiteErrors = self.__analyze_website__(runId, key, website)
            result = dictUtils.extend_dicts(result, websiteResult)
            errors.extend(websiteErrors)
          except NoResultError as e:
            errors.append({'key': key, 'url': e.where, 'message': e.message})
            self.updateRecordState(runId, record, CrawlerState.ERROR, CrawlerAction.COMPLETE)
        if result:
          self.updateEntity(runId, record, arrays={'socials': result}, action=CrawlerAction.COMPLETE)
          count += 1
    except Exception as e:
      errors.append({'message': 'unexpected::{}'.format(e)})
      logger.error('Unexpected', exc_info=True)
    return {'total': total, 'count': count, 'errors': errors}

  def __analyze_website__(self, runId, key, url):
    data, errors = self.__analyze_page__(runId, key, url)
    if data.get('email') and data.get('phone'):
      return data, errors
    for page in self.config.get('page'):
      searchPage = url + page
      try:
        subData, subErrors = self.__analyze_page__(runId, key, searchPage)
        data = dictUtils.extend_dicts(data, subData)
        errors.extend(subErrors)
        break
      except NoResultError as e:
        continue
    return data, errors

  def __analyze_page__(self, runId, key, url):
    logger.info(u'Crawling data - url::{}'.format(url))
    data = {}
    errors = []
    code, content = self.connectURL(url)
    if not code:
      raise NoResultError(content.get('info').get('text'), where=content.get('info').get('url'))
    trackFile = fileUtils.joinPaths(self.tempPrefix, runId, textUtils.optimizeText(url, '_') + '.html')
    logger.debug(u'Crawling data - Key::{} - File::{}'.format(key, trackFile))
    fileUtils.writeTempFile(content, trackFile)
    for social, regex in self.socialRegex.items():
      if social == 'phone':
        try:
          data['phone'] = self.__parsingPhone__(content, regex)
        except CrawlerError as e:
          errors.append({'url': url, 'message': e.message, 'key': key})
        continue
      if social == 'email':
        data[social] = textUtils.search(content, '(href="mailto:)?' + regex, cutoff='(href="mailto:)?')
        continue
      data[social] = textUtils.search(content, 'href="' + regex, cutoff='href="')
    return data, errors

  def __parsingPhone__(self, html, regex):
    phoneRegex = regex.get('regex')
    prefixRegex = regex.get('prefix')
    regexpNS = "http://exslt.org/regular-expressions"
    regexFind = etree.XPath("//*[text()[re:test(., '" + prefixRegex + "')]]", namespaces={'re': regexpNS})
    try:
      tree = etree.HTML(html)
      phones = set()
      hasData = False
      for element in regexFind(tree):
        hasData = True
        inside = textUtils.remove(element.text, prefixRegex).strip()
        phones.add(textUtils.extractToLine(inside, phoneRegex))
        phones.update([textUtils.extractToLine(item.strip(), phoneRegex)
                       for item in element.xpath("../text()") if textUtils.match(item.strip(), phoneRegex)])
        phones.update([textUtils.extractToLine(item.strip(), phoneRegex)
                       for item in element.xpath("./*/text()") if textUtils.match(item.strip(), phoneRegex)])
      if hasData and not phones:
        raise CrawlerError('Cannot parse phone although having prefix')
      return [phone for phone in phones if not textUtils.isEmpty(phone)]
    except ParseError as e:
      raise CrawlerError('Error when parsing html file')
