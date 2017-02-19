import glob
import os
import tempfile
import time
import yaml


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


def createTempFile(filePath):
  metadata = parseFileName(filePath)
  temp = metadata.get('name') + '_' + str(long(time.time())) + metadata.get('ext')
  return os.path.join(tempfile.gettempdir(), temp)
