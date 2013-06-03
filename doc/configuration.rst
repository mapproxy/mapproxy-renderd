Configuration
=============


MapProxy-Renderd shares the configuration file with MapProxy.

To use MapProxy-Renderd you need to specify the address where the MapProxy-Renderd process runs. You can configure this with the ``renderd.address`` option within the ``globals`` section.
MapProxy-Renderd will listen to new requests on this address and MapProxy (the WSGI application) will connect to this address to request new tiles.

Example
-------
::

    globals:
      renderd:
        address: http://localhost:8111

