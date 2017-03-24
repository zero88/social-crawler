#!/usr/bin/python
import copy
import json


def toJson(_dict):
  return json.dumps(_dict)


def fromJson(_json):
  return json.loads(_json, encoding="utf-8")


def restrict(_dict, ignores=[]):
  if not _dict:
    return None
  if not ignores:
    return _dict
  return {k: v for k, v in _dict.iteritems() if k not in ignores}


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
      result.update({k: v for k, v in dictionary.iteritems() if v})
    else:
      result.update(dictionary)
  return result


def extend_dicts(*dict_args):
  result = {}
  for dictionary in dict_args:
    for k, v in dictionary.iteritems():
      if k not in result:
        result.update({k: v})
        continue
      if type(v) is set or type(v) is list:
        value = set(v)
        value.update(result.get(k))
        result.update({k: list(value)})
      elif type(v) is dict:
        a = extend_dicts(result.get(k), v)
        print a
        result.update({k: a})
      else:
        value = set([v])
        value.update([result.get(k)])
        result.update({k: value})
  return result


def deep_copy(_dict):
  return copy.deepcopy(_dict)


def flatten(_dict, prefix='', delimiter='.'):
  ''' Flat dict by delimiter '''
  items = []
  for k, v in _dict.items():
    new_key = prefix + delimiter + str(k) if prefix else str(k)
    if isinstance(v, dict):
      items.extend(flatten(v, prefix=new_key, delimiter=delimiter).items())
    else:
      items.append((new_key, v))
  return dict(items)


def inflate(d, delimiter='.'):
  items = dict()
  for k, v in d.items():
    keys = k.split(delimiter)
    sub_items = items
    for ki in keys[:-1]:
      try:
        sub_items = sub_items[ki]
      except KeyError:
        sub_items[ki] = dict()
        sub_items = sub_items[ki]
    sub_items[keys[-1]] = v
  return items


def build_dict(globalKey, valueKey, _dict):
  return {globalKey: {k: {valueKey: v} for k, v in _dict.items()}}

if __name__ == "__main__":
  test = {'abc': 123, 'hgf': {'gh': [432, 222], 'yu': 433}, 3: 'xx',
          'gfd': 902, 'xzxzxz': {"432": {'0b0b0b': 231}, "43234": 1321}}
  flat = flatten(test)
  print 'Before: ', test
  print 'Flatten: ', flat
  print 'Inflate: ', inflate(flat)
  print merge_dicts(False, {'$set': {'xx': 'a', 'yy.b': 'xx'}}, {})
  arrays = {'$addToSet': {'tags': {'$each': [1, 2, 3]}}}
  print merge_dicts(False, {'$set': {'xx': 'a', 'yy.b': 'xx'}}, arrays)
  print build_dict('$addToSet', '$each', {'tags': [1, 2, 3], 'xxx': ['a', 'b', 'c']})
