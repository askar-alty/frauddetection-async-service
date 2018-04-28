import argparse
import asyncio
import configparser
import json
import logging
import os

import aiohttp
import yaml
from logstash_async.handler import AsynchronousLogstashHandler
from nlp.model import loading

global model, graph
model, graph = loading.init()

with graph.as_default():
    model.get_scores("Check TensorFlow backend")


def build_logger(logstash_config):
    logger = logging.getLogger('python-logstash')
    logger.setLevel(logging.INFO)
    logger.addHandler(AsynchronousLogstashHandler(host=logstash_config.get('logstash_host'),
                                                  port=logstash_config.get('logstash_port'),
                                                  database_path=logstash_config.get('logstash_path')))
    try:
        logger.debug("Test logger debug.")
        logger.info("Test logger info.")
        logger.error("Test logger error")
        logger.warning("Test logger warning.")
    except Exception as error:
        logging.basicConfig(format='[%(asctime)s] %(levelname)s : %(message)s',
                            datefmt='%Y.%m.%d %H:%M:%S',
                            filename=logstash_config['file'] if logstash_config.get('file') else None,
                            filemode='a',
                            level=logging.INFO)

        logging.error(error)
        return None
    return logger


def is_file(file_path):
    return True if file_path and os.path.isfile(file_path) else False


def parse_config(config_path, env):
    conf = configparser.RawConfigParser(allow_no_value=True)
    conf.read(config_path)
    return dict((name, yaml.load(value)) for (name, value) in conf.items(env))


def is_body_from_server_valid(body):
    return True if body.get('text') and isinstance(body['text'], str) else False


def get_response_data(body):
    return {
        'scores': body.get('scores'),
        'sender': {
            'id': body['sender_user'].get('id'),
            'csa_profile_id': body['sender_user'].get('csa_profile_id'),
            'erib_client_id': body['sender_user'].get('erib_client_id'),
            'active': body['sender_user'].get('active'),
            'masked_phone': body['sender_user'].get('masked_phone')
        },
        'message_id': body.get('client_message_id'),
        'conversation_id': body.get('conversation_id')
    }


async def create_ws_session(config, logger):
    session = aiohttp.ClientSession()
    async with session.ws_connect(config.get('url')) as ws:
        logger.info("Open new ws connection")
        async for msg in ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                if msg.data == 'close':
                    await ws.close()
                    break
                else:
                    try:
                        body = json.loads(msg.data)
                    except Exception as error:
                        logger.error(error)
                        break

                    if is_body_from_server_valid(body):
                        with graph.as_default():
                            body['scores'] = model.get_scores(body['text'])
                        logger.info(get_response_data(body))

            elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                logger.error('WS is {}'.format(msg.type))
                break


config = {
    'server': None,
    'logging': None
}

if __name__ == "__main__":
    argument_parser = argparse.ArgumentParser()
    argument_parser.add_argument('--config',
                                 type=str,
                                 nargs='?',
                                 dest='config',
                                 default='docs/application.yml')
    args = argument_parser.parse_args()
    if is_file(args.config):
        config = parse_config(args.config, os.getenv('SYS_ENV') if os.getenv('SYS_ENV') else 'ift')
    if config.get('server', None) and config.get('logging', None):
        logstash_logger = build_logger(config['logging'])
        if logstash_logger:
            logstash_logger.info("Start Client")
            loop = asyncio.get_event_loop()
            loop.run_until_complete(create_ws_session(config['server'], logstash_logger))
            loop.close()
