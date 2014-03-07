#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
varnishsentry
=============

Varnishsentry allows selective submission of grouped varnishd shared memory
log entries to Sentry DSNs.

Check out https://github.com/carlosabalde/varnishsentry for a detailed
description, extra documentation and other useful information.

:copyright: (c) 2014 by Carlos Abalde, see AUTHORS.txt for more details.
:license: GPL, see LICENSE.txt for more details.
'''

from __future__ import absolute_import
import os
import sys
from setuptools import setup, find_packages

if sys.version_info < (2, 6):
    raise Exception('varnishsentry requires Python 2.6 or higher.')

with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'requirements.txt')) as file:
    install_requires = file.read().splitlines()

setup(
    name='varnishsentry',
    version=0.1,
    author='Carlos Abalde',
    author_email='carlos.abalde@gmail.com',
    packages=find_packages(),
    include_package_data=True,
    url='https://github.com/carlosabalde/varnishsentry',
    description=
        'Varnishsentry allows selective submission of grouped varnishd shared '
        'memory log entries to Sentry DSNs.',
    long_description=__doc__,
    license='GPL',
    entry_points={
        'console_scripts': [
            'varnishsentry = varnishsentry.runner:main',
        ],
    },
    classifiers=[
        'Intended Audience :: System Administrators',
        'Operating System :: OS Independent',
    ],
    install_requires=install_requires,
    use_2to3=(sys.version_info[0] == 3)
)
