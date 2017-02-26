from crawler import Crawler, CrawlerAction

from another import AnotherCrawler
from facebook import FacebookCrawler
from google import GoogleCrawler
from instagram import InstagramCrawler
from linkedin import LinkedinCrawler
from twitter import TwitterCrawler

from ..exception import ExecutionError
from ..utils import dictUtils


class CrawlerFactory(object):

  @staticmethod
  def parse(dao, searchQuery):
    crawlers = []
    for method, value in searchQuery.get('methods').iteritems():
      query = dictUtils.deep_copy(searchQuery)
      query['method'] = value
      query['method']['type'] = method
      if method == 'facebook':
        crawlers.append(FacebookCrawler(dao, query))
      elif method == 'google':
        crawlers.append(GoogleCrawler(dao, query))
      elif method == 'instagram':
        crawlers.append(InstagramCrawler(dao, query))
      elif method == 'linkedin':
        crawlers.append(LinkedinCrawler(dao, query))
      elif method == 'twitter':
        crawlers.append(TwitterCrawler(dao, query))
      else:
        crawlers.append(AnotherCrawler(dao, query))
    return crawlers

  @staticmethod
  def execute(action, crawlers):
    for crawler in crawlers:
      if CrawlerAction.SEARCH == action or CrawlerAction.FULL == action:
        crawler.search()
      if CrawlerAction.ACCESS == action or CrawlerAction.FULL == action:
        crawler.access()
      if CrawlerAction.COMPLETE == action or CrawlerAction.FULL == action:
        crawler.complete()