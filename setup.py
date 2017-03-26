import os
import sys

from setuptools import find_packages, setup


def package_files(directory):
  paths = []
  for (path, directories, filenames) in os.walk(directory):
    for filename in filenames:
      paths.append(os.path.join('..', path, filename))
  return paths

config = package_files('athletic/config')
client = package_files('athletic/client/dist')
package_data = config + client + ['logs/dummy.txt']

with open("README.md", 'r') as f:
  long_description = f.read()

setup(
    name='athletic',
    version='1.0.0',
    author='sontt',
    author_email='sontt246@gmail.com',
    long_description=long_description,
    packages=find_packages(exclude=['contrib', 'docs', 'tests']),
    package_data={'athletic': package_data},
    install_requires=[
        'apscheduler==3.3.1', 'pyyaml==3.12', 'pypiwin32', 'pyjwt==1.4.2', 'pymongo==3.4.0', 'requests==2.13.0',
        'flask==0.12', 'flask-restful==0.2.12', 'flask-cors==3.0.2', 'tornado==4.4.2',
        'scrapy==1.2.2', 'splash==2.3.2', 'Twisted==16.6.0', 'selenium==3.3.1', 'lxml==3.4.2',
        'xlrd==1.0.0', 'XlsxWriter==0.9.6'
    ],
    extras_require={
        'test': ['unittest_data_provider'],
    },
    entry_points={
        'console_scripts': [
            'athletic=athletic:main',
        ],
    },
    zip_safe=False
)
