#! /usr/bin/env python3

import logging
import os
import platform
import sys
import uuid

from flask import Flask
import structlog

app = Flask(__name__)
logger = structlog.get_logger()
__id__ = 'proxy'
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


def get_logger():
    return logger.new(
        request_id=str(uuid.uuid4()),
        id=__id__,
        hostname=name,
        app_name=APP_NAME)


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


if __name__ == '__main__':
    setup_logging()
    app.run(host='0.0.0.0', port=80)
