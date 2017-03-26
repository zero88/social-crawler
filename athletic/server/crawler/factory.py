from facebook import FacebookCrawler
from google import GoogleCrawler
from instagram import InstagramCrawler
from linkedin import LinkedinCrawler
from twitter import TwitterCrawler
from website import WebsiteCrawler

from ..exception import ExecutionError
from ..utils import dictUtils
from .crawler import Crawler, CrawlerAction


class CrawlerFactory(object):

  @staticmethod
  def parse(dao, queries):
    crawlers = []
    for query in queries:
      method = query.get('method').get('type')
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
        crawlers.append(WebsiteCrawler(dao, query))
    return crawlers

  @staticmethod
  def execute(action, crawlers):
    for crawler in crawlers:
      if CrawlerAction.SEARCH == action or CrawlerAction.FULL == action:
        crawler.search()
      if CrawlerAction.ACCESS == action or CrawlerAction.FULL == action:
        crawler.access()
      if CrawlerAction.COMPLETE == action or CrawlerAction.FULL == action:
        query = dictUtils.deep_copy(crawler.searchQuery)
        crawler.complete(WebsiteCrawler(crawler.dao, query))
