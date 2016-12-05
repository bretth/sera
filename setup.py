#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup

with open('README.rst') as readme_file:
    readme = readme_file.read()

with open('HISTORY.rst') as history_file:
    history = history_file.read()

requirements = [
    'Click>=6.0',
    'boto3<=2.0',
    'pynacl<=2.0',
    'python-dotenv',
    'requests'
]

test_requirements = [
    # TODO: put package test requirements here
    'pytest',
]

setup(
    name='sera',
    version='0.1.0',
    description="Lower a host firewall with AWS SQS",
    long_description=readme + '\n\n' + history,
    author="Brett Haydon",
    author_email='brett@haydon.id.au',
    url='https://github.com/bretth/sera',
    packages=[
        'sera',
        'sera.providers',
        'sera.commands'
    ],
    package_dir={'sera':
                 'sera'},
    entry_points={
        'console_scripts': [
            'sera=sera.cli:main'
        ]
    },
    include_package_data=True,
    install_requires=requirements,
    license="MIT license",
    zip_safe=False,
    keywords='sera',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
    ],
    test_suite='tests',
    tests_require=test_requirements
)
