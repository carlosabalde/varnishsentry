# -*- coding: utf-8 -*-

'''
Settings and configuration for varnishsentry.

Values will be read from the file specified by the VARNISHSENTRY_CONFIG
environment variable. If not specified, defaults to '/etc/varnishsentry.conf'.

:copyright: (c) 2014 by Carlos Abalde, see AUTHORS.txt for more details.
'''

from __future__ import absolute_import
import os
import imp
from varnishsentry.conf import default


class _Settings(object):
    def __init__(self):
        # Add default configuration.
        self._add_configuration(default)

        # Try to load custom configuration (environment variable or
        # /etc/varnishsentry.conf).
        configuration_file = os.environ.get(
            'VARNISHSENTRY_CONFIG',
            '/etc/varnishsentry.conf')
        if os.path.isfile(configuration_file):
            self.load(configuration_file)

    def load(self, configuration_file):
        with file(configuration_file) as f:
            mod = imp.new_module('varnishsentry.conf._file')
            exec f.read() in mod.__dict__
            self._add_configuration(mod)

    def _add_configuration(self, mod):
        for name in dir(mod):
            if name == name.upper():
                self._add_configuration_item(name, getattr(mod, name))

    def _add_configuration_item(self, name, value):
        setattr(self, name, value)

settings = _Settings()
