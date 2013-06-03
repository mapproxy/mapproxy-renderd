Deployment
==========

You need to start MapProxy in the background. How you do this depends on your system.

On Ubuntu you can use Upstart by creating the file ``/etc/init/mapproxy-renderd.conf``::

    # mapproxy-renderd - MapProxy-Renderd server
    #

    description     "MapProxy-Renderd"

    start on filesystem or runlevel [2345]
    stop on runlevel [!2345]

    respawn

    setuid mapproxy
    setgid mapproxy

    script
      cd /opt/mapproxy
      exec ./bin/mapproxy-renderd -f /etc/opt/mapproxy/mapproxy.yaml \
         --log-conf /etc/opt/mapproxy/renderd_log.ini \
         --renderer 12 --max-seed-renderer 6
    end script


And then start MapProxy-Renderd with ``sudo start mapproxy-renderd``.

