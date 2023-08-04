# coding=utf-8
import argparse

from flask import jsonify, request
from flask import render_template as rt

from en_decrypt.bp import bp
from en_decrypt.before import inits
from app import app_, socket_io
from cons import APP_ENC as APP
from base import MetaFile
import cons


@app_.route('/', methods=['get'], defaults={'a': '', 'e': '', 'f': ''}, endpoint='home')
@app_.route('/webs/<string:f>', defaults={'a': '', 'e': ''}, methods=['get'], endpoint='f')
@app_.route('/webs/<string:a>/<string:f>', methods=['get'], defaults={'e': ''}, endpoint='a')
@app_.route('/webs/<string:a>:<string:e>/<string:f>', methods=['get'], endpoint='e')
def _(a, e, f):
    _bps = [cons.APP_ENC]
    if not a and not f:
        return rt('home.html', **locals())
    if not a:
        return rt('%s.html' % f, **locals())
    if not e:
        return rt('%s/%s.html' % (a, f), **locals())
    return rt('%s/%s/%s.html' % (a, e, f), **locals())


@app_.route('/en_decrypt/index', methods=['get'], endpoint='en_decrypt_index')
def index():
    target = request.args.get('target', '')
    try:
        data = MetaFile.ldr(APP, target, request.args)
    except ValueError as e:
        data = {'status': False, 'message': repr(e)}
    return jsonify(data)


@app_.route('/en_decrypt/view', methods=['get'], endpoint='en_decrypt_view')
def view():
    target = request.args.get('target')
    try:
        data = MetaFile.vw(APP, target, request.args)
    except ValueError as e:
        data = {'status': False, 'message': repr(e)}
    return jsonify(data)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--ip', help='ip', type=str, default='0.0.0.0')
    parser.add_argument('--port', help='port', type=int, default=80)

    ars = parser.parse_args()
    app_.register_blueprint(bp)
    app_.before_first_request_funcs.extend(inits)
    socket_io.run(app_, host=ars.ip, port=int(ars.port), use_reloader=False)
