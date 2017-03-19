import logging

logger = logging.getLogger(__name__)


class BaseError(Exception):
  ''' Base error with common task'''

  def __init__(self, message='', ex=None, level=logging.DEBUG):
    self.message = message
    if ex:
      logger.log(level, message, exc_info=True)
    else:
      logger.log(level, message)


class ValidationError(BaseError):
  ''' Validation error '''

  def __init__(self, message='', ex=None, level=logging.DEBUG):
    super(ValidationError, self).__init__(message, ex, level)


class DatabaseError(BaseError):
  ''' Database error in business aspect '''

  def __init__(self, message='', ex=None):
    super(DatabaseError, self).__init__(message, ex, logging.DEBUG)


class ExistingError(BaseError):
  ''' Existing error with message and existed object '''

  def __init__(self, message, existence):
    super(ExistingError, self).__init__(message, None, logging.DEBUG)
    self.message = message
    self.existence = existence


class RequestError(BaseError):
  ''' Request error from REST-API '''

  def __init__(self, message='', ex=None, level=logging.DEBUG):
    super(RequestError, self).__init__(message, ex, level)


class ExecutionError(BaseError):
  ''' Execution error for controller '''

  def __init__(self, message='', ex=None, level=logging.DEBUG):
    super(ExecutionError, self).__init__(message, ex, level)


class CrawlerError(BaseError):
  ''' Error when crawling '''

  def __init__(self, message='', ex=None, where=None, level=logging.DEBUG):
    super(CrawlerError, self).__init__(message or '' + ('::' + where if where else ''), ex, level)
    self.where = where


class NoResultError(CrawlerError):
  ''' Error when crawling but not find anything '''

  def __init__(self, message='', ex=None, where=None, level=logging.DEBUG):
    super(NoResultError, self).__init__(message, ex, where, level)


class LimitedError(BaseError):
  ''' Error when exceed any limit '''

  def __init__(self, message='', ex=None, currentCount=0, level=logging.DEBUG):
    super(LimitedError, self).__init__(message, ex, level)
    self.currentCount = currentCount
