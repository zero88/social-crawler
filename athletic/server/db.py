# -*- coding: utf-8 -*-
import codecs
import datetime
import json
import logging

import pymongo
from bson import Binary, Code, json_util
from bson.dbref import DBRef
from bson.objectid import ObjectId
from pymongo import ASCENDING, DESCENDING, TEXT, IndexModel, MongoClient

from exception import BaseError, DatabaseError, ValidationError
from utils import dictUtils, fileUtils, textUtils

logger = logging.getLogger(__name__)


class DAO:

  def __init__(self, dbCfg):
    client = MongoClient(dbCfg.get('host'), dbCfg.get('port'))
    self.dbCfg = dbCfg
    self.db = client[dbCfg.get('name')]

  def textSearch(self, collection, query, fields=None, _filter={}, limit=None):
    if query is None:
      raise ValidationError('TextSearch::Missing query')
    textScore = self.dbCfg.get('score_text_search')
    limit = limit or self.dbCfg.get('limit_pagination')
    projection = self.__build_projection__(fields)
    projection['score'] = {'$meta': 'textScore'}
    pipeline = [
        {'$match': {'$text': {'$search': query}}},
        {'$match': _filter},
        {'$project': projection},
        {'$match': {'score': {'$gt': textScore}}},
        {'$sort': {'score': {'$meta': 'textScore'}}},
        {'$limit': limit}
    ]
    logger.debug('Text search in: {} - Pipeline: {}'.format(collection, pipeline))
    return json.loads(json_util.dumps(self.db[collection].aggregate(pipeline)))

  def groupToCount(self, collection, groupBy, query={}, isFK=False, fields=[], sort=-1, limit=None):
    '''
    `isFK` and `fields` will be used to filter displayed column when `groupBy` is foreign key
    '''
    limit = limit or self.dbCfg.get('limit_pagination')
    group = {'_id': '$' + groupBy, 'times': {'$sum': 1}}
    pipeline = [
        {'$match': query},
        {'$group': group},
        {'$sort': {'times': sort}},
        {'$limit': limit}
    ]
    logger.debug('Group Count in: {} - Pipeline: {}'.format(collection, pipeline))
    data = json.loads(json_util.dumps(self.db[collection].aggregate(pipeline)))
    if isFK is True:
      for item in data:
        record = self.findById(item.get('_id').get('$ref'), item.get('_id').get('$id'), fields)
        item['_id'] = json.loads(json_util.dumps(record))
    return data

  def groupView(self, collection, groupBy, query={}, distinctCols=[], mixupCols=[]):
    group = {'_id': '$' + groupBy}
    if distinctCols == [] and mixupCols == []:
      group[collection] = {'$push': '$$ROOT'}
    else:
      group = dictUtils.merge_dicts(False, group, self.buildSetGroupQuery(distinctCols))
      group = dictUtils.merge_dicts(False, group, self.buildListGroupQuery(mixupCols))
    pipeline = [
        {'$match': query},
        {'$group': group}
    ]
    logger.debug('Group View in: {} - Pipeline: {}'.format(collection, pipeline))
    return json.loads(json_util.dumps(self.db[collection].aggregate(pipeline)))

  def findById(self, collection, _id, fields=None):
    if _id is None:
      raise ValidationError('Find by Id::Missing id')
    return self.findOne(collection, {'_id': json_util.loads(json.dumps(_id))}, fields)

  def findOne(self, collection, query, fields=None):
    if query is None:
      raise ValidationError('Find One::Missing query')
    projection = self.__build_projection__(fields)
    logger.debug('Find in: {} - Query: {} - Projection: {}'.format(collection, query, projection))
    instance = self.db[collection].find_one(query, projection=projection)
    return json.loads(json_util.dumps(instance)) if instance else None

  def count(self, collection, query, references=[]):
    logger.debug('Count in: {} - Query: {}'.format(collection, query))
    query = self.__convertRef__(query, references)
    return self.db[collection].find(query).count()

  def list(self, collection, query={}, fields=None, limit=None):
    projection = self.__build_projection__(fields)
    limit = limit or self.dbCfg.get('limit_pagination')
    logger.debug('List in: {} - Query: {} - Fields: {} - Limit: {}'.format(collection, query, projection, limit))
    if limit == -1:
      data = self.db[collection].find(query) if fields == [] else self.db[collection].find(query, projection=projection)
    else:
      data = self.db[collection].find(query).limit(limit) if fields == [] else self.db[collection].find(query, projection=projection).limit(
          limit)
    return json.loads(json_util.dumps(data))

  def insertBulk(self, collection, data):
    try:
      logger.debug('Insert many records into {} - Data {}'.format(collection, data))
      result = self.db[collection].insert_many(data, ordered=False)
      logger.debug('Inserted: {} row(s)'.format(len(result.inserted_ids)))
    except pymongo.errors.BulkWriteError as bwe:
      logger.error('Insert failure - Error {}'.format(bwe))
      logger.debug('Inserted: {} row(s)'.format(bwe.details['nInserted']))
      logger.debug('Failure: {}'.format(bwe.details['writeErrors']))

  def insertOne(self, collection, data, references=[]):
    try:
      if data.get('metadata') is None:
        data['metadata'] = {}
      data['metadata']['created_at'] = datetime.datetime.utcnow()
      data = self.__convertRef__(data, references)
      logger.debug('Insert into {} - Data: {}'.format(collection, data))
      return self.db[collection].insert_one(data)
    except Exception as e:
      raise DatabaseError(ex=e)

  def update(self, collection, query={}, data={}, references=[], arrays={}):
    try:
      data = dictUtils.flatten(data)
      data = self.__convertRef__(data, references)
      data['metadata.modified_at'] = datetime.datetime.utcnow()
      logger.debug('Update to {} - Query: {} - Data: {} - Arrays: {}'.format(collection, query, data, arrays))
      return self.db[collection].update_many(query, dictUtils.merge_dicts(False, {'$set': data}, arrays))
    except Exception as e:
      raise DatabaseError(ex=e)

  def remove(self, collection, query=None):
    if query is None:
      raise DatabaseError(message='Forbid removing all records')
    logger.debug('Remove document in {} - Query: {}'.format(collection, query))
    return self.db[collection].delete_many(query)

  def buildSetGroupQuery(self, fields=[]):
    return {field: {'$addToSet': '$' + field} for field in fields}

  def buildListGroupQuery(self, fields=[]):
    return {field: {'$push': '$' + field} for field in fields}

  def buildSetValues(self, _dict):
    return dictUtils.build_dict('$addToSet', '$each', _dict)

  def buildListValues(self, _dict):
    return dictUtils.build_dict('$push', '$each', _dict)

  def __build_projection__(self, fields=None):
    value = 0 if fields is None else 1
    fields = ['metadata'] if fields is None else fields
    return dictUtils.build_dict_from_keys(fields, value)

  def __convertRef__(self, data, references):
    for ref in references:
      col = ref.get('col')
      collection = ref.get('collection')
      if data.get(col) is None:
        continue
      _id = json_util.loads(json.dumps(data.get(col).get('_id')))
      dbRef = DBRef(collection=collection, id=_id)
      data[col] = dbRef
    return data


class AthleticDB():

  def __init__(self, dao, datafile):
    self.dao = dao
    self.datafile = datafile

  def initialize(self):
    self.__migrate__()
    self.__createIndex__()
    self.__initLocations__()
    self.__recover__()

  def __migrate__(self):
    pass

  def __recover__(self):
    pass
    # paths = self.__getDataFiles__('data', 'log')
    # # lines = []
    # for path in paths:
    #   try:
    #     metadata, artifact = self.__parseMetadata_FromFile__(path)
    #     count, total = 0, 0
    #     with open(path) as f:
    #       for line in f:
    #         total += 1
    #         if textUtils.isEmpty(line):
    #           continue
    #         try:
    #           self.dao.insertOne('teachers', json.loads(u'{}'.format(line.replace('\\', '\\\\')), encoding="utf-8"))
    #           count += 1
    #         except ValueError as e:
    #           logger.exception('Failure::Line {}'.format(total))
    #         except DatabaseError as dbe:
    #           logger.exception('Failure::Line {}'.format(total))
    #     logger.info('Insert into \'teachers\' {} row(s) - Failure: {} row(s) from {}'.format(count, total - count, metadata))
    #   except BaseError as e:
    #     logger.error(e)

  def __createIndex__(self):
    teacherUniqueIndex = IndexModel([('key', ASCENDING), ('metadata.method', ASCENDING)],
                                    name='teacher_unique', unique=True)
    teacherSpecialistIndex = IndexModel([('specialist', ASCENDING)], name='teacher_specialist_index', background=True)
    teacherLocationIndex = IndexModel([('location', ASCENDING)], name='teacher_location_index', background=True)
    self.dao.db.teachers.create_indexes([teacherUniqueIndex, teacherSpecialistIndex, teacherLocationIndex])

    locationIndex = IndexModel([('code', ASCENDING)], name='location_unique', background=True, unique=True)
    locationTextIndex = IndexModel([('label', TEXT)], name='location_full_text_search')
    self.dao.db.locations.create_indexes([locationIndex, locationTextIndex])

    crawlerTransactionUniqueIndex = IndexModel(
        [('runId', ASCENDING)], name='crawler_transaction_unique', background=True, unique=True)
    self.dao.db.crawler_transactions.create_indexes([crawlerTransactionUniqueIndex])

    self.dao.db.builtin_data_registry.create_index([
        ('category', ASCENDING),
        ('version', DESCENDING)
    ], unique=True)

  def __initLocations__(self):
    paths = self.__getDataFiles__('locations', 'json')
    for path in paths:
      try:
        metadata, artifact = self.__parseMetadata_FromFile__(path)
        data = fileUtils.readJson(path, self.datafile).get('locations')
        for location in data:
          location['metadata'] = {'from': artifact}
          self.dao.insertOne('locations', location)
        # self.insertBulk('hookchats', data)
        self.dao.insertOne('builtin_data_registry', metadata)
      except BaseError as e:
        logger.debug(e)

  def __getDataFiles__(self, category, extension):
    return fileUtils.search(self.datafile, category + '-v*' + extension)

  def __parseMetadata_FromFile__(self, filePath):
    name = fileUtils.parseFileName(filePath).get('name')
    category = textUtils.remove(name, r'-v[0-9]+?')
    version = textUtils.extract(name, r'-v[0-9]+?')
    version = version[0][2:] if len(version) > 0 else ''
    if textUtils.isEmpty(version):
      raise ValidationError('File name \'{}\' invalid'.format(filePath))
    if self.dao.findOne('builtin_data_registry', {'category': category, 'version': version}) is not None:
      raise DatabaseError('File name \'{}\' already imported'.format(filePath))
    artifact = category + '@' + version
    return {'file': filePath, 'category': category, 'version': version}, artifact
