import json
import logging
import random
import string

import aiohttp
from aiohttp import web
from nlp.model import loading

global model, graph
model, graph = loading.init()

with graph.as_default():
    model.get_scores("Check TensorFlow backend")


class StatusMessages(object):
    CONNECTED = 'connected'
    SUCCESS = 'success'
    FAILED = 'failed'
    ERROR = 'error'
    CLOSE = 'close'


class ResponseData(object):
    def __init__(self, status_message, message):
        self.status_message = status_message
        self.message = message

    def to_json(self):
        return json.dumps(self.to_dict())

    def to_dict(self):
        return {
            'status': self.status_message,
            'message': self.message
        }

    def get_message(self):
        return self.to_json()


class Response(web.Response):
    _status_code = None
    _content_type = 'text/json'
    _charset = 'utf-8'


class Response200(Response):
    _status_code = 200

    def __init__(self, data):
        super(Response200, self).__init__(status=self._status_code,
                                          content_type=self._content_type,
                                          charset=self._charset,
                                          text=data.get_message())


class Response500(Response):
    _status_code = 500

    def __init__(self, data):
        super(Response500, self).__init__(status=self._status_code,
                                          content_type=self._content_type,
                                          charset=self._charset,
                                          text=data.get_message())


def is_valid_body(body):
    if isinstance(body, dict):
        return True if body.get('text') and len(body) == 1 and isinstance(body['text'], (str, list)) else False
    else:
        return False


async def index(request):
    return Response200(data=ResponseData(status_message=StatusMessages.SUCCESS, message='Hello! I am a fraud detector'))


async def predict_get(request):
    return Response200(data=ResponseData(status_message=StatusMessages.SUCCESS, message={"paths": [
        "/predict/scores",
        "/ws/predict/scores"]}))


async def predict_score_get(request):
    return Response200(data=ResponseData(status_message=StatusMessages.SUCCESS, message='This is score method'))


async def predict_score_post(request):
    try:
        if request.body_exists:
            body = json.loads((await request.read()).decode('utf-8'), encoding='utf-8')
            if is_valid_body(body):
                with graph.as_default():
                    scores = model.get_scores(body['text'])
                return Response200(data=ResponseData(status_message=StatusMessages.SUCCESS, message={'scores': scores}))
            else:
                return Response500(
                    data=ResponseData(status_message=StatusMessages.FAILED, message='Incorrect input data'))
        else:
            return Response500(data=ResponseData(status_message=StatusMessages.FAILED, message='Body is empty.'))
    except Exception as e:
        return Response500(data=ResponseData(status_message=StatusMessages.ERROR, message=str(e)))


async def predict_score_ws(request):
    ws = web.WebSocketResponse()
    is_ws = ws.can_prepare(request)
    if not is_ws:
        return ws

    await ws.prepare(request)

    # Create token for connection
    name = (random.choice(string.ascii_uppercase) + ''.join(random.sample(string.ascii_lowercase * 10, 10)))
    logging.info('%s joined.', name)

    # Send connection response
    response = ResponseData(status_message=StatusMessages.CONNECTED, message=name)
    await ws.send_json(response.to_dict())

    async for msg in ws:
        # Message is text
        if msg.type == aiohttp.WSMsgType.TEXT:
            if msg.data == 'close':
                response = ResponseData(status_message=StatusMessages.CLOSE, message='Ws is closed')
                await ws.send_json(response.to_dict())
                await ws.close()

            # Main block
            else:

                if isinstance(msg.data, str) and len(msg.data) > 5000:
                    response = ResponseData(status_message=StatusMessages.FAILED,
                                            message='Incorrect input data. Size is very big.')
                    await ws.send_json(response.to_json())
                    break
                try:
                    body = json.loads(msg.data)
                except Exception as error:
                    response = ResponseData(status_message=StatusMessages.FAILED,
                                            message='Incorrect input data. '
                                                    'WS connection closed with exception {}.'.format(error))
                    await ws.send_json(data=response.to_dict())
                    break

                if is_valid_body(body):
                    with graph.as_default():
                        scores = model.get_scores(body['text'])
                    response = ResponseData(status_message=StatusMessages.SUCCESS, message={"scores": scores})
                    await ws.send_json(data=response.to_dict())

                else:
                    response = ResponseData(status_message=StatusMessages.FAILED, message='Incorrect input data.')
                    await ws.send_json(data=response.to_dict())
                    break

            logging.info('Body: {} Payload: {}'.format(msg.data, response.to_dict()))

        elif msg.type == aiohttp.WSMsgType.ERROR:
            response = ResponseData(status_message=StatusMessages.ERROR,
                                    message='WS message type is {}.'.format(msg.type))
            logging.error('WS connection closed with exception %s' % ws.exception())
            await ws.send_json(data=response.to_dict())
            break

    logging.info('WS connection closed')
    return ws
