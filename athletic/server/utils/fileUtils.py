import glob
import io
import json
import os
import tempfile
import time

import yaml


def guardFile(fileName):
  with open(fname, "w") as f:
    f.close()
  return fileName


def createDir(dir):
  if os.path.exists(dir):
    return
  try:
    os.makedirs(dir)
  except OSError as exc:  # Guard against race condition
    if exc.errno != errno.EEXIST:
      raise


def parseFileName(filePath):
  parentDir, fileName = os.path.split(filePath)
  name = os.path.splitext(fileName)[0]
  extension = os.path.splitext(fileName)[1]
  return {'dir': parentDir, 'name': name, 'ext': extension}


def joinPaths(parent, *child):
  if parent is None:
    parent = os.path.abspath(os.path.dirname(__file__))
  return os.path.join(parent, *child)


def search(parentDir, wildcard):
  return glob.iglob(joinPaths(parentDir, wildcard))


def readYaml(file):
  with open(file, 'rt') as f:
    return yaml.safe_load(f.read())


def readJson(file, parentDir=None):
  if parentDir:
    file = joinPaths(parentDir, file)
  with open(file, 'rt') as f:
    return json.load(f, encoding='utf-8')


def createTempFile(filePath=None, ext=None):
  if filePath is None and ext is None:
    return None
  if filePath is None:
    temp = str(long(time.time())) + ext
  else:
    metadata = parseFileName(filePath)
    temp = metadata.get('name') + '_' + str(long(time.time())) + metadata.get('ext')
    createDir(os.path.join(tempfile.gettempdir(), metadata.get('dir')))
  return os.path.join(tempfile.gettempdir(), metadata.get('dir'), temp)


def writeTempFile(text, filePath):
  tmp = createTempFile(filePath)
  with io.open(tmp, 'w+', encoding='utf-8') as file:
    file.write(text)
  return os.path.abspath(file.name)
