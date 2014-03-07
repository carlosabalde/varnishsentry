# -*- coding: utf-8 -*-

'''
:copyright: (c) 2014 by Carlos Abalde, see AUTHORS.txt for more details.
'''

from __future__ import absolute_import
import os
import sys
import daemon
import signal
import errno
import time
import multiprocessing
import logging
from lockfile import pidlockfile
from varnishsentry.conf import settings
from varnishsentry.consumer import Consumer


class Daemon(daemon.DaemonContext):
    def __init__(self):
        self._workers = []
        self._shutdown_event = None
        self._logging_queue = None
        self._sigterm = False
        self._sigchld = 0

        super(Daemon, self).__init__(
            pidfile=pidlockfile.PIDLockFile(settings.PIDFILE),
            signal_map={
                signal.SIGTERM: 'sigterm_handler',
                signal.SIGINT: 'sigint_handler',
                signal.SIGCHLD: 'sigchld_handler',
            })

    def start(self, detach=True, debug=False):
        # Check if the service is already running.
        pid = pidlockfile.read_pid_from_pidfile(settings.PIDFILE)
        if pid is not None and self._is_pid_running(pid):
            sys.stderr.write('PID %(pid)s in pidfile "%(pidfile)s" is already running.\n' % {
                'pid': pid,
                'pidfile': settings.PIDFILE,
            })
            sys.exit(1)

        # Remove pidfile (may not exists).
        pidlockfile.remove_existing_pidfile(settings.PIDFILE)

        # Adjust daemon context.
        if not detach:
            self.detach_process = False
            self.stdout = sys.stdout
            self.stderr = sys.stderr

        # Enter daemon context.
        with self:
            # Initializations.
            pid = os.getpid()
            self._shutdown_event = multiprocessing.Event()
            self._logging_queue = multiprocessing.Queue(-1)
            self._init_logger(debug=debug, console=not detach)

            # Log.
            logging.getLogger('varnishsentry').info(
                'Starting varnishsentry service (PID %d)', pid)

            # Launch consumers.
            for id, config in settings.WORKERS.iteritems():
                worker = Consumer(
                    pid,
                    self._shutdown_event,
                    self._logging_queue,
                    id,
                    config,
                    debug)
                self._workers.append(worker)
                worker.start()

            # Periodically check for termination and for terminated workers.
            while not self._sigterm:
                try:
                    # Wait for incoming messages (up to 1 second).
                    record = self._logging_queue.get(True, 1)

                    # Process incoming message.
                    if record is not None:
                        logging.getLogger(record.name).handle(record)
                except:
                    pass

                # Some worker has terminated? => rebuild the list of workers.
                if self._sigchld > 0:
                    workers = []
                    for worker in self._workers:
                        if worker.is_alive():
                            workers.append(worker)
                        else:
                            worker.terminate()
                            logging.getLogger('varnishsentry').error(
                                'Worker %s terminated unexpectedly with status '
                                'code %d', worker.name, worker.exitcode)
                            workers.append(worker.restart())
                    self._workers = workers
                    self._sigchld -= 1

            # Set shutdown event and wait a few seconds for a graceful shutdown
            # of all workers.
            self._shutdown_event.set()
            retries = 5
            while retries > 0:
                if any([worker.is_alive() for worker in self._workers]):
                    retries = retries - 1
                    time.sleep(1)
                else:
                    break

            # After timeout, force shutdown of any alive worker.
            for worker in self._workers:
                if worker.is_alive():
                    worker.terminate()

            # Wait for all workers termination.
            for worker in self._workers:
                worker.join()

        # Clean up and exit.
        pidlockfile.remove_existing_pidfile(settings.PIDFILE)
        logging.getLogger('varnishsentry').info(
            'Shutting down varnishsentry service (PID %d)', pid)
        sys.exit(0)

    def stop(self):
        pid = pidlockfile.read_pid_from_pidfile(settings.PIDFILE)
        if pid is None:
            sys.stderr.write('Failed to read PID from pidfile "%(pidfile)s".\n' % {
                'pidfile': settings.PIDFILE,
            })
            sys.exit(1)
        elif not self._is_pid_running(pid):
            sys.stderr.write('PID %(pid)s in pidfile "%(pidfile)s" is not running.\n' % {
                'pid': pid,
                'pidfile': settings.PIDFILE,
            })
            sys.exit(7)
        else:
            try:
                os.kill(pid, signal.SIGTERM)
                sys.stdout.write('Stopping')
                while self._is_pid_running(pid):
                    sys.stdout.write('.')
                    sys.stdout.flush()
                    time.sleep(1)
                sys.stdout.write(' Ok!\n')
                pidlockfile.remove_existing_pidfile(settings.PIDFILE)
                sys.exit(0)
            except OSError as e:
                sys.stderr.write('Failed to terminate PID %(pid)s: %(message)s.\n' % {
                    'pid': pid,
                    'message': e,
                })
                sys.exit(1)

    def status(self):
        pid = pidlockfile.read_pid_from_pidfile(settings.PIDFILE)
        if pid is None or not self._is_pid_running(pid):
            sys.stdout.write('Stopped.\n')
            sys.exit(3)
        else:
            sys.stdout.write('Running (PID %s).\n' % pid)
            sys.exit(0)

    def sigterm_handler(self, *args):
        # Set flag.
        self._sigterm = True

    def sigint_handler(self, *args):
        sys.stdout.write('Stopping...\n')
        self.sigterm_handler()

    def sigchld_handler(self, *args):
        # Increment counter. This is not 100% signal safe, but it's
        # good enough :)
        self._sigchld += 1

    def _init_logger(self, debug=False, console=False):
        # Init.
        logger = logging.getLogger('varnishsentry')
        logger.propagate = False
        logger.setLevel(
            logging.DEBUG
            if debug
            else settings.LOGGING.get('level', logging.INFO))

        # Fetch & instance formatters.
        formatters = {}
        for id, item in settings.LOGGING.get('formatters', {}).iteritems():
            formatters[id] = logging.Formatter(
                item.get('format'),
                item.get('date_format', None))

        # Add handlers.
        for item in settings.LOGGING.get('handlers', []):
            # Instance handler.
            handler = item['class'](
                *item.get('args', []),
                **item.get('kwargs', {})
            )

            # Set formatter.
            if 'formatter' in item and item['formatter'] in formatters:
                handler.setFormatter(formatters[item['formatter']])

            # Set level.
            if debug:
                handler.setLevel(logging.DEBUG)
            elif 'level' in item and item['level'] is not None:
                handler.setLevel(item['level'])

            # Add handler.
            logger.addHandler(handler)

        # Add console handler?
        if console:
            for id in ('varnishsentry',):
                logger = logging.getLogger(id)
                logger.setLevel(
                    logging.DEBUG
                    if debug
                    else settings.LOGGING.get('level', logging.INFO))
                handler = logging.StreamHandler()
                if debug:
                    handler.setLevel(logging.DEBUG)
                handler.setFormatter(logging.Formatter(
                    '%(asctime)s %(name)s: %(levelname)s %(message)s',
                    '%b %e %H:%M:%S'))
                logger.addHandler(handler)

    def _is_pid_running(self, pid):
        try:
            os.kill(pid, signal.SIG_DFL)
        except OSError as e:
            if e.errno == errno.ESRCH:
                return False
        return True
