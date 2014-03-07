# -*- coding: utf-8 -*-

'''
:copyright: (c) 2014 by Carlos Abalde, see AUTHORS.txt for more details.
'''

from __future__ import absolute_import
import time
import os
import pwd
import grp
import multiprocessing
import logging
import signal
from varnishsentry.conf import settings
from varnishsentry.helpers import log


class Worker(multiprocessing.Process):
    def __init__(self, ppid, shutdown_event, logging_queue, id, config, debug, retries=0):
        super(Worker, self).__init__(name=id)
        self._ppid = ppid
        self._shutdown_event = shutdown_event
        self._logging_queue = logging_queue
        self._config = config
        self._debug = debug
        self._retries = retries
        self._stopping = False
        self._timestamp = int(time.time())

    def restart(self):
        # Build new worker based on the current one.
        worker = self.__class__(
            self._ppid,
            self._shutdown_event,
            self._logging_queue,
            self.name,
            self._config,
            self._debug,
            retries=0 if (int(time.time()) - self._timestamp > 60) else self._retries + 1)

        # Launch.
        worker.start()

        # Return the new instance.
        return worker

    def run(self):
        try:
            # Adjust process GID?
            if 'group' in self._config:
                os.setgid(
                    self._config['group']
                    if isinstance(self._config['group'], int)
                    else grp.getgrnam(self._config['group']).gr_gid)

            # Adjust process UID?
            if 'user' in self._config:
                os.setuid(
                    self._config['user']
                    if isinstance(self._config['user'], int)
                    else pwd.getpwnam(self._config['user']).pw_uid)

            # Initialize logger?
            if self._logging_queue:
                self._init_logger()

            # Adjust inherited signal handlers.
            signal.signal(signal.SIGTERM, signal.SIG_DFL)
            signal.signal(signal.SIGINT, signal.SIG_IGN)
            signal.signal(signal.SIGCHLD, signal.SIG_DFL)

            # Add some delay if required.
            delay = min(self._retries * 0.5, 10.0)
            logging.getLogger('varnishsentry').info(
                'Starting worker. Processing will begin in %.1f seconds', delay)
            time.sleep(delay)

            # Specific worker initialization.
            self._init()

            # Periodically check for termination.
            while not self._stopping:
                # Check if the parent process is still alive.
                if self._ppid is not None and os.getppid() != self._ppid:
                    self._stopping = True
                # Check if the parent process has requested shutdown.
                elif self._shutdown_event and self._shutdown_event.is_set():
                    self._stopping = True
                # Poll worker & wait for the next check.
                else:
                    self._poll()
                    time.sleep(1.0)
        except Exception as e:
            logging.getLogger('varnishsentry').error(
                'Shutting down worker.', exc_info=True)
            raise e
        finally:
            # Specific worker shutdown.
            self._shutdown()

            # Close logging queue.
            self._logging_queue.close()

    def _init(self):
        raise NotImplementedError('Please implement this method.')

    def _poll(self):
        raise NotImplementedError('Please implement this method.')

    def _shutdown(self):
        raise NotImplementedError('Please implement this method.')

    def _init_logger(self):
        # Set custom root logger.
        handler = log.QueueHandler(
            self._logging_queue,
            '%s PID %d' % (self.name, self.pid))
        root = logging.getLogger()
        root.handlers = [handler]
        root.setLevel(
            logging.DEBUG
            if self._debug
            else settings.LOGGING.get('level', logging.INFO))

        # Disable any existing logger.
        for name in logging.Logger.manager.loggerDict.keys():
            logger = logging.getLogger(name)
            logger.handlers = []
            logger.propagate = True
