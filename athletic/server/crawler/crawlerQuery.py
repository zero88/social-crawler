from ..utils import dictUtils


class QueryBuilder(object):

  def __init__(self, methods):
    self.methods = methods
    self.locations = ['au:0', 'us:0', 'gb:0', 'sg:0']
    self.keywords = [
        {'specialist': 'yoga', 'keywords': ['yoga teacher', 'yoga instructor', 'yoga master']},
        {'specialist': 'pilates', 'keywords': ['pilates teacher', 'pilates instructor', 'pilates master']},
        {'specialist': 'MMA', 'keywords': ['mix martial art teacher', 'mix martial art instructor']},
        {'specialist': 'dance', 'keywords': ['dance instructor',
                                             'ballet teacher', 'ballet instructor', 'zumba instructor']}
    ]
    self.counter = {
        'start_page': 1,
        'expected_on_keyword_location': -1,
        'limited': False
    }
    self.query_template = {
        'query': {
            'locations': self.locations,
            'keywords': self.keywords,
            'additional': {}
        },
        'counter': self.counter,
    }

  def build(self, requestBy, filterMethods=[], filterLocations=[], filterSpecs=[], additional={}):
    methods = dictUtils.extract(self.methods, filterMethods) if filterMethods else self.methods
    locations = filter(lambda x: x in filterLocations, self.locations) if filterLocations else self.locations
    keywords = filter(lambda x: x['specialist'] in filterSpecs, self.keywords) if filterSpecs else self.keywords
    queries = []
    for method, auths in methods.items():
      for auth in auths.get('auth'):
        query = dictUtils.deep_copy(self.query_template)
        query['requestBy'] = requestBy
        query['method'] = {'type': method, 'auth': auth}
        query['query']['locations'] = locations
        query['query']['keywords'] = keywords
        query['query']['additional'] = additional
        queries.append(query)
    return queries
