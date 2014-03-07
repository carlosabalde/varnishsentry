# -*- coding: utf-8 -*-

'''
:copyright: (c) 2014 by Carlos Abalde, see AUTHORS.txt for more details.
'''

from __future__ import absolute_import
import re
import time
import datetime
import logging
import threading
from raven import Client
from varnishsentry import api
from varnishsentry.worker import Worker

#
# TODO + RANDOM IDEAS:
#
#   - Use sentry.interfaces.Http & sentry.interfaces.User.
#       - http://sentry.readthedocs.org/en/latest/developer/interfaces/
#       - Custom log message to include user info?
#
#   - Clarify varnishlog -O option. Ordering and non interleaving in guaranteed
#     in varnishlog output?
#       - https://www.varnish-cache.org/docs/3.0/reference/varnishlog.html
#
#   - Can transaction delimiter be improved? Any other approach to gather items?
#

TRANSACTIONS = {
    # Client tx.
    1: {
        'name': 'client',
        'start': ['ReqStart'],
        'end': ['ReqEnd'],
    },

    # Backend tx.
    2: {
        'name': 'backend',
        'start': ['BackendOpen', 'BackendReuse'],
        'end': ['Length', 'BackendClose'],
    },
}

DEFAULT_TIMEOUT = 5

FILTER_LEVELS = ('fatal', 'error', 'warning', 'info', 'debug')


class Consumer(Worker):
    def _init(self):
        # Base initializations.
        self._consuming = False
        self._timeout = self._config.get('timeout', DEFAULT_TIMEOUT)
        self._next_purge = 0

        # Initialize Sentry client.
        self._client = None
        if 'dsn' in self._config:
            self._client = Client(dsn=self._config['dsn'])

        # Connect to libvarnishapi.
        self._vap = api.VarnishAPI(
            opt=self._get_vap_options(self._config.get('options', {})),
            sopath=self._config.get('libvarnishapi', 'libvarnishapi.so.1'))

        # Build list of known tx types.
        self._types = TRANSACTIONS.keys()

        # Normalize tx delimiting tags.
        self._delimiters = {}
        for type, item in TRANSACTIONS.iteritems():
            self._delimiters[type] = {
                'start': [self._vap.VSL_NameNormalize(tag) for tag in item['start']],
                'end': [self._vap.VSL_NameNormalize(tag) for tag in item['end']],
            }

        # Initialize tx filters.
        self._filters = {}
        for tag, filters in self._config.get('filters', {}).iteritems():
            tag = self._vap.VSL_NameNormalize(tag)
            items = []
            for filter in filters:
                # Check regular expression.
                assert \
                    'regexp' in filter, \
                    'All filters must contain a matching regexp.'

                # Build filter.
                item = {
                    'regexp': re.compile(filter['regexp']),
                    'name': filter.get('name', tag),
                    'level': filter.get('level', 'error'),
                }

                # Check level value.
                assert \
                    item['level'] in FILTER_LEVELS, \
                    '"%s" is not a valid filter level.' % item['level']

                # Append filter.
                items.append(item)
            self._filters[tag] = items

        # Initialize tx buffers.
        self._buffers = dict((type, {}) for type in self._types)

        # Launch consumer thread.
        self._thread = threading.Thread(target=self._loop)
        self._thread.daemon = True
        self._thread.start()

    def _poll(self):
        # Is the consumer thread still alive?
        if not self._thread.is_alive():
            raise Exception('Consumer thread has been unexpectedly stopped.')

    def _shutdown(self):
        # If running, stop the consuming thread.
        if self._consuming:
            self._consuming = False

    def _loop(self):
        self._consuming = True
        while self._consuming:
            try:
                self._vap.VSL_Dispatch(self._vap_callBack, priv=False)
            except Exception:
                logging.getLogger('varnishsentry').error(
                    'Got unexpected exception while dispatching VSL item.',
                    exc_info=True)

    def _get_vap_options(self, options):
        result = []
        if options.get('-c', True):
            result.append('-c')
        if options.get('-b', True):
            result.append('-b')
        if options.get('-d', False):
            result.append('-d')
        if options.get('-n'):
            result.append('-n')
            result.append(options['-n'])
        return result

    def _vap_callBack(self, priv, tag, fd, length, spec, ptr, bm):
        # Log incoming tx item.
        logging.getLogger('varnishsentry').debug(
            'Handling new transaction item: '
            'priv=%s, tag=%s, fd=%s, length=%s, spec=%s, ptr=%s, bm=%s.',
            priv, tag, fd, length, spec, ptr, bm)

        # Fetch current UNIX timestamp.
        now = int(time.time())

        # Normalize item fields.
        item = self._vap.normalizeDic(priv, tag, fd, length, spec, ptr, bm)

        # Does the item belong to any relevant tx type?
        if item['type'] in self._types:
            # Is this a brand new transaction?
            if item['tag'] in self._delimiters[item['type']]['start']:
                self._buffers[item['type']][fd] = Transaction(now, item['type'])

            # Has we previously seen the tx?
            tx = self._buffers[item['type']].get(fd)
            if tx is not None:
                # Append the new item to the tx.
                tx.add(item['tag'], item['msg'])

                # Try to match the item.
                if item['tag'] in self._filters:
                    for filter in self._filters[item['tag']]:
                        if filter['regexp'].search(item['msg']):
                            tx.match(
                                item['tag'],
                                item['msg'],
                                filter['name'],
                                filter['level'])

                # Is the tx ending?
                if item['tag'] in self._delimiters[item['type']]['end']:
                    # Remove tx instance from the buffer.
                    del self._buffers[item['type']][fd]

                    # Commit tx
                    self._commit_tx(tx, timeout=False)

        # Time to purge buffered txs?
        if now > self._next_purge:
            self._purge_buffers(now)

    def _purge_buffers(self, now):
        for txs in self._buffers.values():
            for id in txs.keys():
                tx = txs[id]
                # Has the tx timed out?
                if now - tx.timestamp >= self._timeout:
                    # Remove tx instance from the buffer.
                    del txs[id]

                    # Commit tx.
                    self._commit_tx(tx, timeout=True)

        # Set next purgation timestamp.
        self._next_purge = int(time.time()) + 1

    def _commit_tx(self, tx, timeout=False):
        if tx.is_matched and self._client is not None:
            self._client.capture(
                'raven.events.Message',
                message=tx.matched_item,
                data={
                    'timestamp': datetime.datetime.fromtimestamp(tx.timestamp),
                    'logger': 'varnishsentry',
                    'level': tx.matched_level,
                    'tags': {
                        'filter': tx.matched_name,
                        'type': TRANSACTIONS[tx.type]['name'],
                        'worker': self.name,
                    },
                    # 'sentry.interfaces.Message': {
                    #     'message': 'My raw message with interpreted strings like %s',
                    #     'params': ['this'],
                    # },
                    # 'sentry.interfaces.Http': {
                    #     'url': 'http://absolute.uri/foo',
                    #     'method': 'POST',
                    #     'data': {
                    #         'foo': 'bar',
                    #     },
                    #     'query_string': 'hello=world',
                    #     'cookies': 'foo=bar',
                    #     'headers': {
                    #         'Content-Type': 'text/html',
                    #     },
                    #     'env': {
                    #         'REMOTE_ADDR': '192.168.0.1',
                    #     },
                    # },
                    # 'sentry.interfaces.User': {
                    #     'id': 'unique_id',
                    #     'username': 'my_user',
                    #     'email': 'foo@example.com',
                    #     'ip_address': '127.0.0.1',
                    # },
                },
                extra={
                    'timeout': timeout,
                    'items': tx.items,
                    'matched': tx.matched_items,
                })


class Transaction(object):
    def __init__(self, timestamp, type):
        self.timestamp = timestamp
        self.type = type
        self.items = []
        self.matched_item = None
        self.matched_items = []
        self.matched_name = None
        self.matched_level = None

    def add(self, tag, message):
        self.items.append(self._format_item(tag, message))

    def match(self, tag, message, name, level):
        # Format item.
        matched_item = self._format_item(tag, message)

        # Add to the list of matched items.
        self.matched_items.append('[%(level)s/%(name)s] %(item)s' % {
            'name': name,
            'level': level,
            'item': matched_item,
        })

        # Set as the main matched item?
        if self.matched_item is None or \
           FILTER_LEVELS.index(level) < FILTER_LEVELS.index(self.matched_level):
            self.matched_item = matched_item
            self.matched_name = name
            self.matched_level = level

    @property
    def is_matched(self):
        return self.matched_item is not None

    def _format_item(self, tag, message):
        return '[%(tag)s] %(message)s' % {
            'tag': tag,
            'message': message,
        }
