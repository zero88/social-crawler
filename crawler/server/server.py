import logging
import os
from datetime import timedelta

from flask import (Blueprint, Flask, render_template, request,
                   send_from_directory)
from flask_cors import CORS
from flask_restful import Api, Resource, abort, fields, inputs, reqparse
from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop
from tornado.wsgi import WSGIContainer
from werkzeug.exceptions import HTTPException, InternalServerError

import extendJSON
import utils.dictUtils as dictUtils
import utils.textUtils as textUtils


class RESTServer():

    def __init__(self, port, dao, encryptTool=None):
        self.client = '../client/dist/'
        self.assets = {
            'js': os.path.join(self.client, 'js'),
            'css': os.path.join(self.client, 'css'),
            'img': os.path.join(self.client, 'images'),
            'fonts': os.path.join(self.client, 'fonts')
        }
        self.app = Flask(__name__, static_url_path='', template_folder=self.client)
        self.blueprint = Blueprint('api', __name__)
        self.api = Api(self.blueprint)
        self.port = port
        self.dao = dao
        self.encryptTool = encryptTool
        self.config()

    def __root__(self):
        return render_template('index.html')

    def __send_assets__(self, path, category):
        if self.assets.get(category):
            return send_from_directory(self.assets[category], path)
        return ''

    def __favicon__(self):
        return send_from_directory(self.assets['img'], 'favicon.ico', mimetype='image/vnd.microsoft.icon')

    def config(self):
        self.cors = CORS(self.app, resources={r'/api/*': {'origins': '*'}})
        self.app.register_blueprint(self.blueprint)
        self.app.add_url_rule('/', view_func=self.__root__)
        self.app.add_url_rule('/js/<path:path>', view_func=self.__send_assets__, defaults={'category': 'js'})
        self.app.add_url_rule('/css/<path:path>', view_func=self.__send_assets__, defaults={'category': 'css'})
        self.app.add_url_rule('/images/<path:path>', view_func=self.__send_assets__, defaults={'category': 'img'})
        self.app.add_url_rule('/fonts/<path:path>', view_func=self.__send_assets__, defaults={'category': 'fonts'})
        self.app.add_url_rule('/favicon.ico', view_func=self.__favicon__)

        self.api.add_resource(Auth.init(self.dao), '/api/auth/<auth_id>')
        extendJSON.support_jsonp(self.api)

    def __setPing__(self, ioloop, timeout):
        ioloop.add_timeout(timeout, lambda: self.__setPing__(ioloop, timeout))

    def start(self):
        http_server = HTTPServer(WSGIContainer(self.app))
        http_server.listen(self.port)
        ioloop = IOLoop.current()
        self.__setPing__(ioloop, timedelta(seconds=2))
        ioloop.start()


class Auth(Resource):
    pass
