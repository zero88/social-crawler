#!/usr/bin/python
import argparse
import logging
import logging.config
import os
from email import message_from_string

import yaml
from pkg_resources import get_distribution

import server.utils.textUtils as textUtils
from server.app import Background


def __setup_logging__(logConfig='logging.yml', logLevel=logging.INFO):
  root = os.path.abspath(os.path.dirname(__file__))
  path = os.path.join(root, 'config', logConfig)
  if os.path.exists(path):
    with open(path, 'rt') as f:
      config = yaml.safe_load(f.read())
    for k, handler in config['handlers'].items():
      file = handler.get("filename", None)
      if file is None:
        continue
      handler['filename'] = os.path.join(root, 'logs', file)
    logging.config.dictConfig(config)
    # print logging.config
  else:
    logging.basicConfig(level=logLevel)


def __setupApp__(appConfig, defaultCfg='app.yml'):
  if(appConfig is None or appConfig.strip() is not defaultCfg):
    root = os.path.abspath(os.path.dirname(__file__))
    path = os.path.join(root, 'config', defaultCfg)
  else:
    path = appConfig.strip()
  if os.path.exists(path):
    with open(path, 'rt') as f:
      return yaml.safe_load(f.read())
  else:
    raise Exception('App config: ' + appConfig + ' not found')


def main(*v):
  __setup_logging__()
  pkgInfo = (v and v[0]) or message_from_string(get_distribution(__name__).get_metadata('PKG-INFO'))
  logger = logging.getLogger(__name__)
  parser = argparse.ArgumentParser(usage=pkgInfo['Description'])
  parser.add_argument("-c", "--config", action="store", default="", help="A configuration file (yaml)")
  parser.add_argument('-v', '--version', action='version', version=pkgInfo['Version'])
  args = parser.parse_args()

  logger.info('===== Welcome Crawler :: Athletic Teacher Collector =====')
  appCfg = __setupApp__(args.config)

  print textUtils.isEmpty('a')
  Background().start()
  # encryptTool = Encrypt(appCfg['encrypt'])
  # server = RESTServer(appCfg['server'], encryptTool)
  # server.start()


if __name__ == "__main__":
  main({'Version': 'dev', 'Description': ''})
