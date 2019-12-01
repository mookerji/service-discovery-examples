#! /usr/bin/env python3

import logging
import os
import platform
import sys
import time
import uuid
import yaml

from flask import Flask, jsonify
from readerwriterlock import rwlock
import attr
import structlog

app = Flask(__name__)
logger = structlog.get_logger()
__id__ = 'proxy'
name = platform.node()
APP_NAME = os.getenv('APP_NAME')
NODE_CONFIG_FILE = os.getenv('NODE_CONFIG_FILE')


def setup_logging():
    logging.basicConfig(
        format="%(message)s", stream=sys.stdout, level=logging.INFO)
    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.KeyValueRenderer(sort_keys=True)
        ],
        context_class=structlog.threadlocal.wrap_dict(dict),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    log = logging.getLogger('werkzeug')
    log.disabled = True


def get_logger():
    return logger.new(
        request_id=str(uuid.uuid4()),
        id=__id__,
        hostname=name,
        app_name=APP_NAME)


@attr.s
class ServiceRegistry(object):
    config_path = attr.ib(default=NODE_CONFIG_FILE)
    _config = attr.ib(default={})
    _lock = attr.ib(default=rwlock.RWLockRead())

    def config_exists(self):
        return os.path.exists(self.config_path)

    def load_config(self):
        with open(self.config_path) as file:
            with self._lock.gen_wlock():
                self._config = yaml.load(file, Loader=yaml.FullLoader)
            return True

    def get_config(self):
        with self._lock.gen_rlock():
            return self._config


registry = ServiceRegistry()


@app.route('/')
def hi():
    log = get_logger()
    log.info("request", method='GET', route='/')
    return 'HI'


@app.route('/healthz')
def healthz():
    log = get_logger()
    log.info("request", method='GET', route='healthz')
    return 'OK'


@app.route('/statusz')
def statusz():
    log = get_logger()
    log.info("request", method='GET', route='statusz')
    return jsonify(registry.get_config())


@app.route('/_hooks/reload_config', methods=['POST'])
def _reload_config():
    log = get_logger()
    registry.load_config()
    log.info('registry-reload-success')
    log.info("request", method='POST', route='_hooks/reload_config')
    return 'OK'


if __name__ == '__main__':
    setup_logging()
    log = logger.new(id=__id__, hostname=name, app_name=APP_NAME)
    max_retries = 10
    num_retries = 0
    while not registry.config_exists() and num_retries < max_retries:
        log.info('registry-waiting')
        time.sleep(1)
    if not registry.config_exists():
        log.error("registry-not-found")
        sys.exit(1)
    config = registry.load_config()
    log.info('registry-load-success')
    app.run(host='0.0.0.0', port=80, threaded=True)
