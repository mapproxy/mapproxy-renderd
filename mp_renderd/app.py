from __future__ import with_statement
import os
import sys
import atexit
import optparse
import multiprocessing

from mp_renderd.wsgi import RenderdApp
from mp_renderd.broker import Broker, WorkerPool, SeedWorker, RenderQueue
from mapproxy.config.loader import load_configuration

import logging
log = logging.getLogger(__name__)

def init_logging(log_config_file=None, verbose=False):
    if log_config_file:
        from logging import config
        config.fileConfig(log_config_file,
            defaults={'here': os.path.dirname(log_config_file)},
            disable_existing_loggers=False)
    else:
        if verbose:
            logging.getLogger('mapproxy').setLevel(logging.INFO)
            log.setLevel(logging.DEBUG)
            logging.basicConfig(level=logging.DEBUG)
        else:
            logging.basicConfig(level=logging.INFO)

def fatal(msg):
    log.fatal(msg)
    print >>sys.stderr, msg
    sys.exit(2)


def main():
    parser = optparse.OptionParser()
    parser.add_option("-f", "--proxy-conf",
        dest="conf_file", default='mapproxy.yaml',
        help="MapProxy configuration")
    parser.add_option("--renderer", default=None, type=int,
        help="Number of render processes.")
    parser.add_option("--max-seed-renderer", default=None, type=int,
        help="Maximum --renderer used for seeding.")
    parser.add_option("--pidfile")
    parser.add_option("--log-config", dest="log_config_file")
    parser.add_option("--verbose", action="store_true", default=False)

    options, args = parser.parse_args()

    init_logging(options.log_config_file, options.verbose)

    conf = load_configuration(options.conf_file, renderd=True)
    broker_address = conf.globals.renderd_address
    if not broker_address:
        fatal('mapproxy config (%s) does not define renderd address' % (
            options.conf_file))
    broker_address = broker_address.replace('localhost', '127.0.0.1')
    broker_port = int(broker_address.rsplit(':', 1)[1]) # TODO

    tile_managers = {}
    with conf:
        for mapproxy_cache in conf.caches.itervalues():
            for tile_grid_, extent_, tile_manager in mapproxy_cache.caches():
                tile_manager._expire_timestamp = 2**32 # future ~2106
                tile_managers[tile_manager.identifier] = tile_manager

    if options.renderer is None:
        pool_size = multiprocessing.cpu_count()
    else:
        pool_size = options.renderer
    if options.max_seed_renderer is None:
        max_seed_renderer = pool_size
    else:
        max_seed_renderer = min(options.max_seed_renderer, pool_size)
    non_seed_renderer = pool_size - max_seed_renderer
    process_priorities = [50] * non_seed_renderer + [0] * max_seed_renderer

    log.debug('starting %d processes with the following min priorities: %r',
        pool_size, process_priorities)

    def worker_factory(in_queue, out_queue):
        return SeedWorker(tile_managers, conf.base_config,
            in_queue=in_queue,
            out_queue=out_queue)

    worker_pool = WorkerPool(worker_factory, pool_size=pool_size)
    task_queue = RenderQueue(process_priorities)

    if options.pidfile:
        with open(options.pidfile, 'w') as f:
            f.write(str(os.getpid()))
        def remove_pid():
            os.unlink(options.pidfile)
        atexit.register(remove_pid)

    try:
        broker = Broker(worker_pool, task_queue)
        broker.start()

        app = RenderdApp(broker)
        import eventlet
        from eventlet import wsgi
        wsgi.server(eventlet.listen(('127.0.0.1', broker_port)), app)

    except KeyboardInterrupt:
        print >>sys.stderr, 'exiting...'
        return 2
    except Exception:
        log.fatal('fatal error, terminating', exc_info=True)
        raise

if __name__ == '__main__':
    main()