import re


def extract(text, regex):
  return re.findall(re.compile(regex), text)


def extractToLine(text, regex):
  matches = re.compile(regex).match(text)
  if matches:
    return matches.group(1)
  return None


def remove(text, regex):
  if isEmpty(text):
    return ''
  text = re.sub(regex, r'', text).strip()
  return re.sub(r'\s+', r' ', text).strip()


def optimizeText(label):
  key = label.lower().strip()
  key = re.sub(r'[^a-z0-9 ]+', r'', key).strip()
  key = re.sub(r'\s+', r' ', key).strip()
  return key


def split(text, regex):
  return re.compile(regex).split(text)


def isEmpty(text):
  return text is None or text.strip() == ''

if __name__ == '__main__':
