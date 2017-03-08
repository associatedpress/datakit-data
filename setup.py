"""

datakit-data
---------------

A `datakit <https://pypi.python.org/pypi/datakit-core/>`_ plugin to simplify use of
Amazon S3 as a data store for data science projects.

* `Code <https://github.com/associatedpress/datakit-data>`_
* `Docs <http://datakit-data.readthedocs.io/en/latest/>`_

"""
from setuptools import setup, find_packages

requirements = [
    'awscli',
    'cliff',
    'datakit-core>=0.2.1',
]

test_requirements = [
    'pytest'
    'pytest-catchlog'
    'pytest-mock==1.5.0',
]

setup(
    name='datakit-data',
    version='0.1.0',
    description="A datakit plugin to manage data assets on AWS S3.",
    long_description=__doc__,
    author="Serdar Tumgoren",
    author_email='stumgoren@ap.org',
    url='https://github.com/associatedpress/datakit-data',
    packages=find_packages(),
    include_package_data=True,
    entry_points={
        'datakit.plugins': [
            'data:init= datakit_data:Init',
            'data:push= datakit_data:Push',
            'data:pull= datakit_data:Pull',
        ]
    },
    install_requires=requirements,
    license="ISC license",
    zip_safe=False,
    keywords='datakit',
    classifiers=[
        'Development Status :: 3 - Alpha',
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
