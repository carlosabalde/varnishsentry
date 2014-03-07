# -*- coding: utf-8 -*-

'''
:copyright: (c) 2014 by Carlos Abalde, see AUTHORS.txt for more details.
'''

from __future__ import absolute_import
import os
import sys
from optparse import OptionParser
from varnishsentry.conf import settings
from varnishsentry.runner import daemon


def _start(args, parser):
    # Initialize.
    parser.add_option(
        '', '--daemon', action='store_true', dest='daemon', default=False,
        help='launch service as a daemon')
    parser.add_option(
        '', '--debug', action='store_true', dest='debug', default=False,
        help='launch service in debug mode')
    options = _init(args, parser)

    # Start.
    daemon.Daemon().start(detach=options.daemon, debug=options.debug)


def _stop(args, parser):
    # Initialize.
    _init(args, parser)

    # Stop.
    daemon.Daemon().stop()


def _status(args, parser):
    # Initialize.
    _init(args, parser)

    # Status.
    daemon.Daemon().status()


def _settings(args, parser):
    # Initialize.
    _init(args, parser)

    # Dump settings.
    import inspect
    from varnishsentry.conf import default
    sys.stdout.write(inspect.getsource(default))


def _init(args, parser):
    # Parse command line arguments.
    (options, args) = parser.parse_args(args)

    # Load settings file.
    if options.config:
        settings.load(options.config)

    # Done!
    return options


def main():
    # Compose help message.
    help = '''Usage: %(cmd)s <command> [--config=CONFIG] [<options>]

  %(header)s[daemon]%(endc)s
  start [--daemon] [--debug]:
      Starts workers.

  stop:
      Stops workers.

  status:
      Shows service status.

  %(header)s[misc]%(endc)s
  settings:
      Dumps sample configuration file.

''' % {
        'cmd': os.path.basename(sys.argv[0]),
        'header': '\033[92m',
        'endc': '\033[0m',
    }

    # Check base arguments.
    if len(sys.argv) > 1:
        command = '_' + sys.argv[1].replace('-', '_').replace('.', '_')
        if command in ('_start', '_stop', '_status', '_settings',):
            parser = OptionParser('usage: %prog ' + sys.argv[1] + ' [options]')
            parser.add_option(
                '', '--config', dest='config', default=None,
                help='set configuration file',
                metavar='CONFIG')
            getattr(sys.modules[__name__], command)(sys.argv[2:], parser)
        else:
            sys.stderr.write(help)
            sys.exit(1)
    else:
        sys.stderr.write(help)
        sys.exit(1)


if __name__ == '__main__':
    main()
