# coding=utf-8
import argparse

from flask import jsonify, request
from flask import Flask
from flask_socketio import SocketIO
from flask import render_template as rt

from en_decrypt.bp import bp
from en_decrypt.before import inits
from cons import APP_ENC as APP
from base import MetaFile
import cons

_ = Flask(__name__, template_folder='bs5/templates', static_folder='bs5/static')
_.config.update(
    WTF_CSRF_SECRET_KEY='x32dc5UTM6eWa8C3qgYRt12u7oiFwSrN',
    WTF_CSRF_TIME_LIMIT=14400,
    WTF_CSRF_ENABLED=False,
    PERMANENT_SESSION_LIFETIME=144000,
    SESSION_REFRESH_EACH_REQUEST=True,
    SEND_FILE_MAX_AGE_DEFAULT=3600,
    FLASK_DB_QUERY_TIMEOUT=0.000001,
    SCHEDULER_API_ENABLED=True,
    SCHEDULER_EXECUTORS={"default": {"type": "threadpool", "max_workers": 20}},
    SCHEDULER_JOB_DEFAULTS={"coalesce": True, "max_instances": 3},
)
# init websocket
socket_io = SocketIO(
    _,
    async_mode='threading',
    ping_timeout=6000,
    ping_interval=60
)


@_.route('/', methods=['get'], defaults={'a': '', 'e': '', 'f': ''}, endpoint='home')
@_.route('/webs/<string:f>', defaults={'a': '', 'e': ''}, methods=['get'], endpoint='f')
@_.route('/webs/<string:a>/<string:f>', methods=['get'], defaults={'e': ''}, endpoint='a')
@_.route('/webs/<string:a>:<string:e>/<string:f>', methods=['get'], endpoint='e')
def html(a, e, f):
    _bps = [cons.APP_ENC]
    if not a and not f:
        return rt('home.html', **locals())
    if not a:
        return rt('%s.html' % f, **locals())
    if not e:
        return rt('%s/%s.html' % (a, f), **locals())
    return rt('%s/%s/%s.html' % (a, e, f), **locals())


@_.route('/en_decrypt/index', methods=['get'], endpoint='en_decrypt_index')
def index():
    target = request.args.get('target', '')
    try:
        data = MetaFile.ldr(APP, target, request.args)
    except ValueError as e:
        data = {'status': False, 'message': repr(e)}
    return jsonify(data)


@_.route('/en_decrypt/view', methods=['get'], endpoint='en_decrypt_view')
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
    _.register_blueprint(bp)
    for f in inits:
        f()
    socket_io.run(_, host=ars.ip, port=int(ars.port), use_reloader=False, allow_unsafe_werkzeug=True)
