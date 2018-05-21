#!/usr/bin/env python3

from setuptools import setup

def readme():
  with open('README.md') as f:
    return f.read()

setup(name='microsimulation',
  version='0.0.1',
  description='Population and household microsimulation',
  long_description=readme(),
  url='https://github.com/nismod/microsimulation',
  author='Andrew P Smith',
  author_email='a.p.smith@leeds.ac.uk',
  license='MIT',
  packages=['microsimulation'],
  zip_safe=False,
  install_requires=['distutils_pytest', 'humanleague', 'ukcensusapi'],
  dependency_links=['git+git://github.com/virgesmith/humanleague.git#egg=humanleague',
                    'git+git://github.com/virgesmith/UKCensusAPI.git#egg=ukcensusapi',
                    'git+git://github.com/nismod/population.git#egg=population'],
  test_suite='nose.collector',
  tests_require=['nose'],
  python_requires='>=3'
  #scripts=['scripts/run_microsynth.py']
)
