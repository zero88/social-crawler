#!/usr/bin/python
# encoding=utf8
import re


def match(text, regex):
  return not isEmpty(text) and re.compile(regex).match(text)


def search(text, regex, cutoff=''):
  if isEmpty(text):
    return ''
  search = re.finditer(re.compile(regex, flags=re.I), text)
  return list(set([remove(match.group(), cutoff) for match in search])) if search else ''


def extract(text, regex):
  return re.findall(re.compile(regex), text) if not isEmpty(text) else ''


def extractToLine(text, regex):
  matches = match(text, regex)
  return matches.group() if matches else ''


def remove(text, regex):
  if isEmpty(text):
    return ''
  text = re.sub(regex, r'', text).strip()
  return re.sub(r'\s+', r' ', text).strip()


def optimizeText(text, delimiter=r' '):
  if isEmpty(text):
    return ''
  key = text.lower().strip()
  key = re.sub(r'[^a-z0-9 ]+', r'', key).strip()
  key = re.sub(r'\s+', delimiter, key).strip()
  return key


def split(text, regex):
  return re.compile(regex).split(text)


def isEmpty(text):
  return text is None or text.strip() == ''


def encode(text):
  if isEmpty(text):
    return ''
  if type(text) is not unicode:
    return text
  return text.encode('utf-8')


def decode(text):
  if type(text) is unicode:
    return text
  return text.decode('utf-8')
