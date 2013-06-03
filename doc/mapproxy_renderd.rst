.. _mapproxy-renderd:

################
mapproxy-renderd
################


The commandline tool ``mapproxy-renderd`` starts the background process of MapProxy-Renderd.


Options
-------

.. program:: mapproxy-renderd

.. cmdoption:: -f <mapproxy.yaml>, --mapproxy-conf <mapproxy.yaml>

  The path to the MapProxy configuration. Required.

.. cmdoption:: --renderer <INT>

  Number of render processes. Defaults to the number of CPUs.

.. cmdoption:: --max-seed-renderer <INT>

  Maximum number of render processes that are used for seeding.

.. cmdoption:: --log-config <log.ini>

  .ini configuration file for Python logging.

