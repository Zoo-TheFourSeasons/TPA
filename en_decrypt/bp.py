# -*- coding: utf-8 -*-
import traceback

from flask import Blueprint, request, jsonify

from en_decrypt.assistant import EncryptHelper as Helper
from app import socket_io
from base import MetaWebSocket
from cons import APP_ENC as APP
import independence as ind


class CryptoNameSpace(MetaWebSocket):

    def __init__(self, *args, **kwargs):
        MetaWebSocket.__init__(self, *args, **kwargs)
        self.apis = {
            'en_decrypt:execute': self.api_execute,
        }
        self.events = {
            'EXECUTE': self.execute
        }

    def execute(self, data):
        print('api_execute', data)
        params = data.get('params')
        aes = params.get('psw_aes')
        stream = params.get('psw_stream')
        nonce = params.get('nonce')
        tp = params.get('type')

        yfd = Helper()
        for target in params.get('target').split(','):
            try:
                yfd.security_by_golang(APP, tp, aes, stream, nonce, target)
            except Exception as e:
                yfd.print('failed in api_execute: %s' % e)
                yfd.print(traceback.format_exc())


socket_io.on_namespace(CryptoNameSpace('/en_decrypt'))

bp = Blueprint('en_decrypt', __name__)


@bp.route('/en_decrypt/', methods=['get'], endpoint='en_decrypt')
@ind.wex
def en_decrypt():
    psw_aes = request.args.get('psw_aes')
    psw_stream = request.args.get('psw_stream')
    nonce = request.args.get('nonce')
    _type = request.args.get('type')
    Helper.security_by_golang(APP, request.args.get('target'), _type, psw_aes, nonce, psw_stream)
    return jsonify({'status': True})


@bp.route('/en_decrypt/separate', methods=['get'], endpoint='separate')
@ind.wex
def separate():
    _type = request.args.get('type')
    target = request.args.get('target')
    max_size = request.args.get('max_size')
    Helper.separate(APP, target, _type, max_size)
    return jsonify({'status': True})
