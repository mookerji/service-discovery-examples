#! /usr/bin/env python3

import logging
import os
import platform
import random
import sys
import time
import uuid
import yaml

from flask import Flask, jsonify, request, after_this_request
from readerwriterlock import rwlock

import attr
import requests
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


def get_logger(request_id=uuid.uuid4()):
    return logger.new(
        request_id=str(request_id),
        id=__id__,
        hostname=name,
        app_name=APP_NAME,
        user_agent=request.headers.get('user-agent'),
    )


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


@app.route('/services/<arg>')
def dispatch(arg):
    request_id = uuid.uuid4()
    log = get_logger(request_id)
    log.info("request", method='GET', route='/', resource=arg)

    @after_this_request
    def add_header(response):
        response.headers['x-request-id'] = str(request_id)
        return response

    config = registry.get_config()
    if not config['services']:
        return jsonify(error='no_services_found'), 500
    # Select a random host from one of the services.
    for s in config['services']:
        if s['name'] == arg:
            num_hosts = len(s['hosts'])
            addr = s['hosts'][random.randrange(num_hosts)]
            url = 'http://%s:%d/' % (addr, 80)
            headers = {'x-request-id': str(request_id), 'user-agent': APP_NAME}
            log.info("proxy", method='GET', node_addr=addr, service=s['name'])
            return requests.get(url, headers=headers).text
    return jsonify(error='invalid_service_name', name=arg), 400


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


@app.route('/_hooks/reload/config', methods=['POST'])
def _reload_config():
    log = get_logger()
    log.info("request", method='POST', route='_hooks/reload/config')
    registry.load_config()
    log.info('registry-reload-success')
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
