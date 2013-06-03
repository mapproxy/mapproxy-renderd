Introduction
============

MapProxy-Renderd is a background process that creates new tiles for MapProxy.


.. note:: MapProxy-Renderd is in an early state. Configuration and the command line interface might change in future releases.


Motivation
----------

MapProxy implements the Web Server Gateway Interface (WSGI) which makes it easy to deploy it within the Apache HTTP server, or as a separate HTTP server behind Nginx or Varnish, without the need to write specific code for each deployment solution.

A WSGI application is always bound to a request: A request comes in, the application processes it and returns a response. MapProxy can't process anything between requests, or start processing anything that lasts longer than a request. This is one of the reasons that the MapProxy seeding tool is a separate command, executed outside of the web application [0]_.

.. [0] Technically it would be possible to start new processes that would outlive a request, but depending on the deployment it will result in unexpected behaviour and hard to track bugs.

WSGI applications are also not able to *talk* to other requests. MapProxy thus can't know what other MapProxy requests are doing, e.g how many requests to a certain sources are already being processed. This is the reason MapProxy needs to create lock files for some tasks.

A background process that runs during the whole time that the WSGI application itself runs would allow to process background tasks and to defer tasks to some time after the response was sent.

MapProxy-Renderd is such a background process. With this long running process MapProxy is able to orchestrate tasks independent to any HTTP requests.
It is possible to run tasks in the background (like seeding), to run tasks after the initiating request was processed (like generating tiles for the next level), to collect statistics for all requests and much more.


Current implementation
----------------------

The current version of MapProxy-Renderd is able to create new tiles on request. These requests can come from the MapProxy WSGI application or the MapProxy seed tool.

MapProxy-Renderd implements a priority queue that allows to handle requests with different urgencies. This allows to seed new tiles in the background, while allowing MapProxy to generate tiles required for live WMS requests with a higher priority. The concurrency of MapProxy-Renderd is configurable. You can also leave a few of these processes free for on-demand requests.

For example: You can have 10 render processes, where at maximum 6 of them are used for seeding. If now 8 requests for new tiles come in, than it will dispatch 4 of them immediately to the idle processes (6 of the 10 are used by the seeding). The other 4 requests will be handled one by one after one of the running processes finishes. New seed requests will be queued and have to wait till there are at least 5 free processes (4 are keept free for non-seeding requests).

MapProxy-Renderd is a separate command that you need to start before MapProxy. It uses the same configuration file as MapProxy.


Future
------

While MapProxy-Renderd is already useful, there are a lot of ideas how it could be extended.

A few ideas:

- include MapProxy seeding tool to allow automatic re-seeding
- add RESTful API to MapProxy-Renderd seeding to allow to trigger reseeding from remote script
- use heuristics to pre-generate tiles the user will likely request next (e.g. tiles from the the next level)
- let MapProxy return "waiting" images when the tiles are not generated within a short time, but keep generating the tiles in the background
- let MapProxy return expired tiles with a short cache timeout and regenerate the tiles in background, so that the next request will return fresh tiles

Please get in touch with us if you want to contribute to one of these features.
