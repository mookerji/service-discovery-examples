#! /usr/bin/env python3

import json
import logging
import os
import platform
import socket
import sys
import uuid

from flask import Flask, request
import requests
import structlog

app = Flask(__name__)
logger = structlog.get_logger()
__id__ = 'node'
name = platform.node()
APP_NAME = os.getenv('APP_NAME')


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


@app.route('/')
def hi():
    request_id = request.headers.get('x-request-id')
    log = get_logger(request_id)
    log.info("request", method='GET', route='/')
    return 'HI'


@app.route('/healthz')
def healthz():
    log = get_logger()
    log.info("request", method='GET', route='healthz')
    return 'OK'


def register_task():
    """
    Registers Consul task
    """
    address = socket.gethostbyname(name)
    data = {
        'Name': APP_NAME,
        'ID': name,
        'Tags': [__id__, 'node'],
        'Address': address,
        'Port': 80,
        'Check': {
            'http': 'http://%s/healthz' % address,
            'interval': '10s'
        }
    }
    registry_url = 'http://registry:8500/v1/agent/service/register'
    try:
        return requests.put(registry_url, data=json.dumps(data)).ok
    except:
        return False


if __name__ == '__main__':
    setup_logging()
    log = logger.new(id=__id__, hostname=name, app_name=APP_NAME)
    if not register_task():
        log.error('registry-failure')
        sys.exit(1)
    log.info("registry-success")
    app.run(host='0.0.0.0', port=80, threaded=True)
