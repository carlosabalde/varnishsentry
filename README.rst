**Varnishsentry** allows selective submission of grouped `varnishd shared memory log <https://www.varnish-cache.org/docs/master/reference/varnishlog.html>`_ entries to `Sentry <https://github.com/getsentry/sentry>`_ DSNs.

Varnishlog entries are gathered together into client or backend transactions. Each transaction is matched against a set of configurable filtering regular expressions. Transactions matching any filter are submitted to a Sentry DSN for proper alerting and post-mortem analysis.

Varnishsentry runs as a daemon service supporting multiple workers. Each worker runs in a separate process, fetching varnishlog entries using `https://github.com/xcir/python-varnishapi <Shohei Tanaka's Python libvarnish API wrapper>`_, and using a customized Sentry DSN and set of filtering rules.

Why varnishsentry?
==================

`Sentry <http://getsentry.com>`_ is a great open source realtime event logging and aggregation platform easily integrable in any web application. On the other hand, `Varnish Cache <http://www.varnish-cache.org>`_ is a powerful, blazingly fast and flexible web accelerator.

Varnish Cache is so flexible that **moving web logic from the backend to the caching layer** is possible (and highly recommended) in some cases. There are strong limitations on what kind of logic can be moved into Varnish Cache, but the logic moved there will be embedded and compiled into Varnish Cache itself, and it will run thousand times faster than in the typical PHP, Python or Java backends.

When moving complex domain logic from the backend to Varnish Cache, at some point you will need to figure out how to deal with error handling, alerting, etc. That's the reason varnishsentry was created for: when dealing with errors in your customized VCL or VMODs, simply use the standard Varnish Cache logging capabilities (i.e. ``std.log()``). Varnishsentry will look for error messages matching some patterns in the varnishd shared memory log, and submit errors together with all available context information to some previously defined Sentry DSN.

QuickStart
==========

Coming soon :)

Configuration
=============

Coming soon :)

Resources
=========

Coming soon :)
