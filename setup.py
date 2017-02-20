import os
import sys

from setuptools import find_packages, setup


def package_files(directory):
  paths = []
  for (path, directories, filenames) in os.walk(directory):
    for filename in filenames:
      paths.append(os.path.join('..', path, filename))
  return paths

config = package_files('crawler/config')
client = package_files('crawler/client/dist')
package_data = config + client + ['logs/dummy.txt']

with open("README.md", 'r') as f:
  long_description = f.read()

setup(
    name='crawler',
    version='1.0.0',
    author='sontt',
    author_email='sontt246@gmail.com',
    long_description=long_description,
    packages=find_packages(exclude=['contrib', 'docs', 'tests']),
    package_data={'crawler': package_data},
    install_requires=[
        'pyyaml', 'pymongo', 'requests', 'xlrd', 'XlsxWriter'
    ],
    extras_require={
        'test': ['unittest_data_provider'],
    },
    entry_points={
        'console_scripts': [
            'crawler=crawler:main',
        ],
    },
    zip_safe=False
)
