#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup

with open('README.rst') as readme_file:
    readme = readme_file.read()

with open('HISTORY.rst') as history_file:
    history = history_file.read()

requirements = [
    'awscli',
    'cliff',
    'datakit-core',
]

test_requirements = [
    'pytest'
]

setup(
    name='datakit-data',
    version='0.1.0',
    description="A datakit plugin to manage data assets on AWS S3.",
    long_description=readme + '\n\n' + history,
    author="Serdar Tumgoren",
    author_email='stumgoren@ap.org',
    url='https://github.com/associatedpress/datakit-data',
    packages=[
        'datakit_data',
    ],
    package_dir={'datakit_data':
                 'datakit_data'},
    include_package_data=True,
    entry_points={
        'datakit.plugins': [
            #'fancyplugin:greet= datakit_data.greet:Greet',
        ]
    },
    install_requires=requirements,
    license="ISC license",
    zip_safe=False,
    keywords='datakit-data',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: ISC License (ISCL)',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
    ],
    test_suite='tests',
    tests_require=test_requirements
)
