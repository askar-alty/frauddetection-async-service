import asyncio
import logging
import os
from logging.handlers import TimedRotatingFileHandler

import routes
from aiohttp import web
from aiohttp.abc import AbstractAccessLogger

FORMAT = '[%(asctime)s] %(levelname)s : %(message)s'


def build_logger():
    logger = logging.getLogger('')
    handler = TimedRotatingFileHandler('logs/log.log', when="midnight", interval=1)
    handler.setLevel(10)
    handler.setFormatter(logging.Formatter(FORMAT))
    logger.addHandler(handler)
    return logger


class AccessLogger(AbstractAccessLogger):
    def log(self, request, response, time):
        self.logger.info('{} {} {} {} {}'.format(request.remote, request.method, request.path, time, response.status))


def init_application(loop, logger):
    app = web.Application(loop=loop, logger=logger)
    routes.setup_routes(app)
    return app


def start_server(server_config, logger):
    loop = asyncio.get_event_loop()
    app = init_application(loop, logger)
    web.run_app(app, host=server_config.get('host'), port=server_config.get('port'), access_log_class=AccessLogger)
    loop.close()


if os.getenv('SYS_ENV') and os.getenv('SYS_ENV') == 'dev':
    start_server({'host': '127.0.0.1', 'port': '8082'}, build_logger())

else:
    application = init_application(loop=asyncio.get_event_loop(), logger=AccessLogger(log_format=FORMAT,
                                                                                      logger=build_logger()))
