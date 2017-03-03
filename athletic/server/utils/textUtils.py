import re


def extract(text, regex):
  if isEmpty(text):
    return ''
  return re.findall(re.compile(regex), text)


def extractToLine(text, regex):
  if isEmpty(text):
    return ''
  matches = re.compile(regex).match(text)
  if matches:
    return matches.group(1)
  return None


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
