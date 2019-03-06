# -*- coding: utf-8 -*-
import base64
import json
import os
import re
from abc import ABC
from concurrent.futures import ThreadPoolExecutor

import tornado.ioloop
import tornado.web
from tornado import httpserver
from tornado.concurrent import run_on_executor

from jano import available_cpu_count, extract_data
from jano.models.ArticleObject import ArticleObject
from pales.controllers.BuilderController import predict

if os.environ.get('CORE_MULTIPROCESSING'):
    MAX_WORKERS = available_cpu_count()
    print("Tornado: Utilizará multi-processamento")
else:
    MAX_WORKERS = available_cpu_count()
    print("Tornado: Um único núcleo será utilizado")


def decode_base64(data, altchars=b'+/'):
    """Decode base64, padding being optional.

    :param data: Base64 data as an ASCII byte string
    :returns: The decoded byte string.

    """
    data = bytes(data, 'utf-8')  # normalize
    data = re.sub(rb'[^a-zA-Z0-9%s]+' % altchars, b'', data)  # normalize
    missing_padding = len(data) % 4
    if missing_padding:
        data += b'=' * (4 - missing_padding)
    return base64.b64decode(data, altchars).decode("utf-8")


class APIHandler(tornado.web.RequestHandler, ABC):
    executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)

    def set_default_headers(self):
        self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header("Access-Control-Allow-Headers", "x-requested-with")
        self.set_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')

    @run_on_executor
    def background_task(self, i):
        """ Isto sera executado em uma Pool. """
        try:
            result = predict(i)
            return str(result[0])
        except Exception as e:
            self.set_status(500)
            return str(e.__str__())

    @tornado.web.gen.coroutine
    def get(self, query):
        """ Chama a tarefa de fundo de forma assíncrona """
        data = decode_base64(query)
        res = yield self.background_task(data)
        metadados = extract_data(data)
        original: ArticleObject = metadados['original']
        data = {
            "request": data,
            "info": {
                "title": original.titulo,
                "descricao": original.descricao,
                "domain": original.domain
            },
            "response": res
        }
        self.write(json.dumps(data))


class Teste(tornado.web.RequestHandler, ABC):
    async def teste(self):
        return "hello"

    async def get(self):
        self.write(await self.teste())


def make_app():
    return tornado.web.Application([
        (r"/", Teste),
        (r"/api/([\s\S]*)", APIHandler),
    ])


if __name__ == "__main__":
    print("Tornado it!")
    app = make_app()
    port = os.environ.get('PORT') if os.environ.get('PORT') else 8888

    if os.environ.get('CORE_MULTIPROCESSING'):
        server = httpserver.HTTPServer(app)
        server.bind(port)
        server.start(0)  # forks one process per cpu
    else:
        app.listen(port)
    tornado.ioloop.IOLoop.current().start()
