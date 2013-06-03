Installation
============


MapProxy-Renderd only depends on MapProxy. Refer to the `MapProxy installation documentation <http://mapproxy.org/docs/nightly/install.html>`_.

Install MapProxy-Renderd
------------------------

To install MapProxy-Renderd with ``pip`` you need to call::

  pip install MapProxy-Renderd

You specify the release version of MapProxy-Renderd. E.g.::

  pip install MapProxy-Renderd==1.6.0

or to get the latest 1.6.x version::

  pip install "MapProxyRenderd>=1.6.0,<=1.6.99"

To check if the MapProxy-Renderd was successfully installed, you can call the `mapproxy-renderd` command.
::

    mapproxy-renderd --version
