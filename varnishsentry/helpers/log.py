# -*- coding: utf-8 -*-

'''
:copyright: (c) 2014 by Carlos Abalde, see AUTHORS.txt for more details.
'''

from __future__ import absolute_import
import logging
import traceback


class QueueHandler(logging.Handler):
    def __init__(self, queue, prefix):
        super(QueueHandler, self).__init__()
        self._queue = queue
        self._prefix = prefix

    def emit(self, record):
        try:
            # Add message prefix.
            record.msg = '[%s] %s' % (self._prefix, record.msg)

            # Add exception as message suffix (it cannot be pickled to be
            # delivered to other process).
            if record.exc_info is not None:
                record.msg = \
                    record.msg + '\n\n' + \
                    ''.join(traceback.format_exception(*record.exc_info))
                record.exc_info = None

            # Add to multiprocessing queue.
            self._queue.put_nowait(record)
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            self.handleError(record)
