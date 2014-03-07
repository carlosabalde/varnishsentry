# -*- coding: utf-8 -*-
# -*- mode: python -*-
# vi: set ft=python :

'''
varnishsentry configuration.

:copyright: (c) 2014 by Carlos Abalde, see AUTHORS.txt for more details.
'''

from __future__ import absolute_import

###############################################################################
## DAEMON.
###############################################################################

PIDFILE = '/var/run/varnishsentry.pid'

###############################################################################
## WORKERS.
###############################################################################

WORKERS = {
    # Example worker.
    'sample': {
        # Required: Sentry DSN where matched transactions will be submitted to.
        # Any supported Raven protocol can be used here (UDP, etc.).
        'dsn': 'http://public:secret@example.com/1',

        # Required: only transactions matching some filter will be submitted to
        # Sentry. All regular expressions are labeled with a string that will
        # be used as a tag when delivering some transaction to Sentry. Defaults
        # to no filters at all (i.e. nothing will be submitted to Sentry).
        'filters': {
            'VCL_Log': [
                ('error', r'^\[ERROR\].*'),
            ],
            'TxStatus': [
                ('500', r'^500$'),
            ],
        },

        # Optional: run the worker process using some specific UID & GID. Note
        # that launching varnishsentry as root is required when using this
        # option. Defaults to same UID & GID that the master varnishsenry process.
        'user': 'nobody',
        'group': 'nogroup',

        # Optional: the worker behavior can be fine-tuned with some varnishlog
        # options. Only -c, -b, -d & -n are supported here. More information:
        #
        #   - https://www.varnish-cache.org/docs/master/reference/varnishlog.html
        #
        # Defaults to 'varnishlog -c -b'.
        'options': {
            '-c': True,
            '-b': True,
            '-d': False,
            '-n': 'acme',
        },

        # Optional: libvarnishapi path may be manually specified. Defaults to
        # 'libvarnishapi.so.1'
        'libvarnishapi': '/usr/lib/libvarnishapi.so.1',

        # Optional: broken transactions are discarded after some timeout. Defaults
        # to 5 seconds.
        'timeout': 5,
    },
}

###############################################################################
## LOGGING.
###############################################################################

import logging
from logging import FileHandler
#from raven.handlers.logging import SentryHandler
#from logging.handlers import SysLogHandler

LOGGING = {
    'level': logging.INFO,
    'formatters': {
        'verbose': {
            'format': '%(asctime)s %(name)s: %(levelname)s %(message)s',
            'date_format': '%b %e %H:%M:%S',
        },
    },
    'handlers': [
        {
            'class': FileHandler,
            'args': ['/var/log/varnishsentry.log'],
            'formatter': 'verbose',
        },
        # {
        #     'class': SentryHandler,
        #     'level': logging.ERROR,
        #     'args': ['http://public:secret@example.com/1'],
        #     'formatter': 'verbose',
        # },
        # {
        #    'class': SysLogHandler,
        #    'level': logging.ERROR,
        #    'kwargs': {
        #        'address': ('127.0.0.1', 514),
        #        'facility': SysLogHandler.LOG_SYSLOG,
        #    },
        # },
    ],
}
