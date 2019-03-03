# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import os
import configparser
import radguestauth.auth as auth

from flask import Flask, request, jsonify

from radguestauth.core import GuestAuthCore


guestauthcore = GuestAuthCore()


def json_rest_unpack(data):
    """
    FreeRADIUS JSON data is formatted as follows (see mod_rest config file):

    "<attributeN>": {
          "type":"<typeN>",
          "value":[...]
    }

    This takes the first item from value, so the result is

    "<attributeN>": "<value>"
    """
    res = dict()
    try:
        for key in data:
            res[key] = str(data[key]['value'][0])
    except TypeError:
        # ignore malformed data
        pass
    return res


def create_app():
    # use INI config instead of Flask config, such that radguestauth stays
    # completely independent from the config format of Flask
    # Default config:
    guestauth_cfg = {'chat': 'udp'}

    confpath = os.environ.get('RADGUESTAUTH_CONFIG')
    if confpath:
        cparser = configparser.ConfigParser()
        cparser.read(confpath)
        if 'radguestauth' in cparser.sections():
            guestauth_cfg = dict(cparser['radguestauth'])

    guestauthcore.startup(guestauth_cfg)

    app = Flask(__name__)

    @app.route('/')
    def info():
        return 'radguestauth REST server running'

    @app.route('/authorize', methods=['POST'])
    def authorize():
        data = json_rest_unpack(request.json)
        state, attr_dict = guestauthcore.authorize(data)

        if state == auth.REJECT:
            return (jsonify({}), 401)

        if state == auth.NO_OP:
            return (jsonify(''), 204)

        return jsonify(attr_dict)

    @app.route('/post-auth', methods=['POST'])
    def post_auth():
        data = json_rest_unpack(request.json)
        attr_dict = guestauthcore.post_auth(data)
        if not attr_dict:
            return (jsonify(''), 204)

        return jsonify(attr_dict)

    @app.route('/drop-expired')
    def drop_expired():
        guestauthcore.drop_expired_users()
        return 'OK'

    return app


# -- gunicorn config --

# More than one worker would result in undefined behavior, as there is only
# one GuestAuthCore instance available.
workers = 1
# The standard worker does not support persistent connections.
# Thread-based workers result in deadlocks on exit due to SleekXMPP Threads
# (probably because two thread pools are used, see
# https://stackoverflow.com/questions/47147328/thread-wait-for-tstate-lock-never-returns).
# eventlet works just fine.
worker_class = 'eventlet'


# Exit hook for proper shutdown. Has to be called from the worker process,
# therefore worker_exit and not on_exit.
def worker_exit(server, worker):
    guestauthcore.shutdown()


# Enable log output. See CONFIG_DEFAULTS in gunicorn.glogging
logconfig_dict = dict(
    version=1,
    disable_existing_loggers=False,

    root={"level": "DEBUG", "handlers": ["console"]},
    loggers={
        # remove specific loggers as they are covered by root logger
    },
    handlers={
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "generic",
            "stream": "ext://sys.stdout"
        },
        "error_console": {
            "class": "logging.StreamHandler",
            "formatter": "generic",
            "stream": "ext://sys.stderr"
        },
    },
    formatters={
        "generic": {
            # add logger name
            "format": "%(asctime)s [%(process)d - %(name)s] [%(levelname)s] %(message)s",
            "datefmt": "[%Y-%m-%d %H:%M:%S %z]",
            "class": "logging.Formatter"
        }
    }
)

# -- end gunicorn-specific config --


# When running the Flask development server instead of gunicorn:
# use atexit to shutdown, see
# https://stackoverflow.com/questions/30739244/python-flask-shutdown-event-handler/30739397
# atexit.register(guestauthcore.shutdown)

# development server:
# $ FLASK_APP=radguestauth.server flask run

# gunicorn:
# $ gunicorn "radguestauth.server:create_app()" -c python:radguestauth.server
