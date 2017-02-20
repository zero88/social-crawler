#!/usr/bin/python
import copy
import json


def toJson(_dict):
  return json.dumps(_dict)


def fromJson(_json):
  return json.loads(_json)


def extract(_dict, keys=[], keepIfNotExist=False):
  if not _dict:
    return None
  if not keys:
    return _dict
  if keepIfNotExist is True:
    return {k: _dict.get(k, None) for k in keys}
  return {k: _dict[k] for k in keys if k in _dict}


def build_dict_from_keys(keys, defaultValue):
  return dict((key, defaultValue) for key in keys)


def build_dict(objects, key):
  return dict((obj[key], dict(obj)) for obj in objects)


def merge_dicts(skipEmpty, *dict_args):
  '''
  Given any number of dicts, shallow copy and merge into a new dict,
  precedence goes to key value pairs in latter dicts.
  '''
  result = {}
  for dictionary in dict_args:
    if skipEmpty:
      result.update({k: v for k, v in dictionary.iteritems() if v not in [None, '']})
    else:
      result.update(dictionary)
  return result


def deep_copy(_dict):
  return copy.deepcopy(_dict)


if __name__ == '__main__':
  d1 = {'a': 1, 'b': None, 'c': 2, 'd': 'abc', 'e': 1}
  d2 = {'a': None, 'b': 'xxx', 'c': 3, 'd': '', 'e': 0}
  print merge_dicts(True, d1, d2)
  print merge_dicts(False, d1, d2)
  print d1.get('x')
  filters = [dict(name='name', op='like', val='%y%')]
  print filters

  print 'xxxxxxx'
  print build_dict_from_keys(['ab', 'cd'], 1)

  QUESTION_MODEL = {
      'chatbot': '',
      'key': '',
      'label': '',
      'synonyms': [],
      'dept': '',
      'answer': '',
      'submittedby': '',
      'metadata': {}
  }
  d = deep_copy(QUESTION_MODEL)
  d['chatbot'] = 'xyz'
  print d
  print QUESTION_MODEL

  a = 5
  b = None
  print b or a
  from model import QuestionModel
  d.get('synonyms').append({'word': 'aa', 'substitute': ['', '']})
  d.get('synonyms').append({'word': '', 'substitute': ['', '']})
  d.get('synonyms').append({'word': 'xx', 'substitute': ['a', '']})
  print QuestionModel.optimizeSynonyms(d)

  print extractSubDict({'word': 'aa', 'substitute': ['', '']}, ['word'])
  print extractSubDict({'word': 'aa', 'substitute': ['', '']}, ['word', 'xx'], True)
