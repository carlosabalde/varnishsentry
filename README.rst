**Varnishsentry** allows selective submission of grouped `varnishd shared memory log <https://www.varnish-cache.org/docs/master/reference/varnishlog.html>`_ entries to `Sentry <https://github.com/getsentry/sentry>`_ DSNs.

Varnishlog entries are gathered together into client or backend transactions. Each transaction is matched against a set of configurable filtering regular expressions. Transactions matching any filter are submitted to a Sentry DSN for proper alerting and post-mortem analysis.

Varnishsentry runs as a daemon service supporting multiple workers. Each worker runs in a separate process, fetching varnishlog entries using `Shohei Tanaka's Python libvarnish API wrapper <https://github.com/xcir/python-varnishapi>`_, and using a customized Sentry DSN and set of filtering rules.

Varnishsentry is sponsored by `Allenta Consulting <http://www.allenta.com>`_, the Varnish Software `partner for Spain and Portugal <https://www.varnish-software.com/partner/allenta-consulting>`_.

How it works?
=============

Use the standard Varnish Cache logging capabilities to log error, warning, etc. conditions while processing incoming requests::

    sub vcl_recv {
        ...

        if (std.random(0, 100) < 50) {
            std.log("[WTF] We have just flipped a coin and it has landed on the bad side!");
        }

        ...
    }

Set up varnishsentry (``/etc/varnishsentry.conf``) accordingly to match and submit previously logged messages::


    ...


    WORKERS = {
        'test': {
            'dsn': 'http://public:secret@example.com/1',
            'filters': {
                'VCL_Log': [
                    {
                        'regexp': r'^\[WTF\].*',
                        'name': 'wtf',
                        'level': 'warning',
                    },
                ],
            },
            'user': 'nobody',
            'group': 'nogroup',
            ...
       },
    }

    ...

And that's it. You will start receiving Sentry alerts including all relevant varnishlog entries in order to do a proper post-mortem analysis.

.. image:: https://github.com/carlosabalde/varnishsentry/raw/master/extras/screenshot.png

Why varnishsentry?
==================

`Sentry <http://getsentry.com>`_ is a great open source realtime event logging and aggregation platform easily integrable in any web application. On the other hand, `Varnish Cache <http://www.varnish-cache.org>`_ is a powerful, blazingly fast and flexible web accelerator.

Varnish Cache is so flexible that **moving web logic from the backend to the caching layer** is possible (and highly recommended) in some cases. There are strong limitations on what kind of logic can be moved into Varnish Cache, but the logic moved there will be embedded and compiled into Varnish Cache itself, and it will run thousand times faster than in the typical PHP, Python or Java backends.

When moving complex domain logic from the backend to Varnish Cache, at some point you will need to figure out how to deal with error handling, alerting, etc. That's why varnishsentry was created: when dealing with errors, warnings, etc. in your customized VCL files or VMODs, simply use the standard Varnish Cache logging capabilities (i.e. ``std.log(...)`` or ``WSP(sp, SLT_Error, ...)``). Varnishsentry will look for messages matching some patterns in the varnishd shared memory log. Those log entries will be submitted to some previously defined Sentry DSN together with all available context information.

QuickStart
==========

1. Install varnishsentry and all its dependencies::

    ~$ sudo pip install varnishsentry

2. Create a varnishsentry configuration template running the following command::

    ~$ sudo varnishsentry settings > /etc/varnishsentry.conf

   Edit ``/etc/varnishsentry.conf`` and set your preferences. Don't be afraid. The file is `extensibility documented <https://github.com/carlosabalde/varnishsentry/blob/master/varnishsentry/conf/default.py>`_ :)

3. Optionally, you can check varnishsentry has been proverly configured running the following command::

    ~$ sudo varnishsentry start --debug

   Wait a few seconds. If you don't see errors hit CTRL+C to exit.

4. In a production environment you should run varnishsentry as an OS service. Use whatever software you are most familiar with, such as upstart, supervisord or a simple init.d script. Check out the `sample init.d script <https://github.com/carlosabalde/varnishsentry/blob/master/extras/init.d/varnishsentry>`_ if you need some inspiration.
