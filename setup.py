"""

datakit-data
---------------

A `datakit <https://pypi.python.org/pypi/datakit-core/>`_ plugin to simplify use of
Amazon S3 as a data store for data science projects..

* `Code <https://github.com/associatedpress/datakit-data>`_
* `Docs <http://datakit-data.readthedocs.io/en/latest/>`_

"""
from setuptools import setup

requirements = [
    'awscli',
    'cliff',
    'cookiecutter>=1.5.0',
    'datakit-core',
]

test_requirements = [
    'pytest',
    'pytest-cookies',
]

setup(
    name='datakit-data',
    version='0.1.0',
    description="A datakit plugin to manage data assets on AWS S3.",
    long_description=__doc__,
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
            #'data:setup= datakit_data:Setup',
            #'data:push= datakit_data:Push',
            #'data:pull= datakit_data:Pull',
        ]
    },
    install_requires=requirements,
    license="ISC license",
    zip_safe=False,
    keywords='datakit-data',
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
