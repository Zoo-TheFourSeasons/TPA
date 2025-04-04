# -*- coding: utf-8 -*-
"""app
"""
import os
import logging

from apscheduler import events
from flask import Flask
from flask_socketio import SocketIO
from flask_apscheduler import APScheduler
from flask import jsonify
from flask import render_template as rt
from flask import request as r

import independence as ind
import ins
import cons
from base import MetaFile


def create_app():
    """create app
    """
    _app = Flask(__name__, template_folder='bs5/templates', static_folder='bs5/static')
    _app.debug = True
    _app.config.update(
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
    return _app


def job_missed(event):
    """Job missed event."""
    print('job_missed', event)


def job_error(event):
    """Job error event."""
    print('job_error', event)


def job_executed(event):
    """Job executed event."""
    print('job_executed', event)


def job_added(event):
    """Job added event."""
    print('job_added', event)


def job_removed(event):
    """Job removed event."""
    print('job_removed', event)


def job_submitted(event):
    """Job scheduled to run event."""
    print('job_submitted', event)


app_ = create_app()

# init APScheduler
scheduler = APScheduler()
scheduler.init_app(app_)
scheduler.start()
scheduler.add_listener(job_missed, events.EVENT_JOB_MISSED)
scheduler.add_listener(job_error, events.EVENT_JOB_ERROR)
scheduler.add_listener(job_executed, events.EVENT_JOB_EXECUTED)
scheduler.add_listener(job_added, events.EVENT_JOB_ADDED)
scheduler.add_listener(job_removed, events.EVENT_JOB_REMOVED)
scheduler.add_listener(job_submitted, events.EVENT_JOB_SUBMITTED)

# init websocket
socket_io = SocketIO(
    app_,
    # async_mode='threading',
    ping_timeout=6000,
    ping_interval=60
)


@app_.route('/', methods=['get'], defaults={'a': '', 'e': '', 'f': ''}, endpoint='home')
@app_.route('/webs/<string:f>', defaults={'a': '', 'e': ''}, methods=['get'], endpoint='f')
@app_.route('/webs/<string:a>/<string:f>', methods=['get'], defaults={'e': ''}, endpoint='a')
@app_.route('/webs/<string:a>:<string:e>/<string:f>', methods=['get'], endpoint='e')
@ind.wex
# @ind.rtk
@ind.c4s(log=True)
def _(a, e, f):
    if a and a not in ins.ins_bps:
        return jsonify({'status': False, 'message': 'app disabled: %s' % a})

    _bps = ins.ins_bps
    if not a and not e:
        app = r.args.get('app', '')
        ae = app.split(':')
        edp = 'home' if not app else ae[1] if ':' in app else ae[0]
    else:
        edp = a if not e else e

    if not a and not f:
        return rt('home.html', **locals())
    if not a:
        return rt('%s.html' % f, **locals())
    if not e:
        return rt('%s/%s.html' % (a, f), **locals())
    return rt('%s/%s/%s.html' % (a, e, f), **locals())


@app_.route('/<string:a>:<string:e>/index', methods=['get'], endpoint='e_index')
@app_.route('/<string:a>/index', methods=['get'], defaults={'e': ''}, endpoint='index')
@ind.wex
@ind.rtk
@ind.c4s(log=True)
def _(a, e):
    if a not in ins.ins_bps:
        return jsonify({'status': False, 'message': 'app disabled: %s' % a})

    t = r.args.get('target', '')
    if a in (cons.APP_ZOO, cons.APP_SEC, cons.APP_ENC, cons.APP_MED, cons.APP_SQU) or e == cons.EDP_DF:
        suffix = None
    else:
        suffix = '.' + e if e else a
    if a == cons.APP_TIM:
        from timing.assistant import TimingHelper as Ass
    elif a == cons.APP_STA:
        from star.assistant import StarHelper as Ass
    elif a == cons.APP_MED:
        from media.assistant import MediaHelper as Ass
    else:
        Ass = MetaFile
    f = Ass.ldr
    return jsonify(f(':'.join((a, e)) if e else a, t, r.args, suffix))


@app_.route('/<string:a>:<string:e>/delete', methods=['get'], endpoint='e_delete')
@app_.route('/<string:a>/delete', methods=['get'], defaults={'e': ''}, endpoint='delete')
@ind.wex
@ind.rtk
@ind.c4s(log=True)
def _(a, e):
    if a not in ins.ins_bps:
        return jsonify({'status': False, 'message': 'app disabled: %s' % a})
    if a == cons.APP_TIM:
        from timing.assistant import TimingHelper as Ass
        f = Ass.remove
    else:
        f = MetaFile.de
    return jsonify(f(':'.join((a, e)) if e else a, r.args.get('target')))


@app_.route('/<string:a>:<string:e>/touch', methods=['get'], endpoint='e_touch')
@app_.route('/<string:a>/touch', methods=['get'], defaults={'e': ''}, endpoint='touch')
@ind.wex
@ind.rtk
@ind.c4s(log=True)
def _(a, e):
    if a not in ins.ins_bps:
        return jsonify({'status': False, 'message': 'app disabled: %s' % a})

    t = r.args.get('target')
    if a == cons.APP_TIM:
        from timing.assistant import TimingHelper as Ass
        f = Ass.update if os.path.exists(Ass.aep(a, e, t)) else MetaFile.th
    else:
        f = MetaFile.th

    text = r.args.get('text')
    return jsonify(f(text, ':'.join((a, e)) if e else a, t))


@app_.route('/<string:a>:<string:e>/mkdir', methods=['get'], endpoint='e_mkdir')
@app_.route('/<string:a>/mkdir', methods=['get'], defaults={'e': ''}, endpoint='mkdir')
@ind.wex
@ind.rtk
@ind.c4s(log=True)
def _(a, e):
    if a not in ins.ins_bps:
        return jsonify({'status': False, 'message': 'app disabled: %s' % a})

    t = r.args.get('target')
    if '&' in t or ',' in t:
        return jsonify({'status': False, 'message': 'target can not contain special char: &,'})
    return jsonify(MetaFile.mdr(':'.join((a, e)) if e else a, t))


@app_.route('/<string:a>:<string:e>/view', methods=['get'], endpoint='e_view')
@app_.route('/<string:a>/view', methods=['get'], defaults={'e': ''}, endpoint='view')
@ind.wex
@ind.rtk
@ind.c4s(log=True)
def _(a, e):
    if a not in ins.ins_bps:
        return jsonify({'status': False, 'message': 'app disabled: %s' % a})

    t = r.args.get('target')
    return jsonify(MetaFile.vw(':'.join((a, e)) if e else a, t, r.args))


@app_.route('/<string:a>:<string:e>/download', methods=['get'], endpoint='e_dd')
@app_.route('/<string:a>/download', methods=['get'], defaults={'e': ''}, endpoint='dd')
@ind.wex
@ind.rtk
@ind.c4s(log=True)
def _(a, e):
    if a not in ins.ins_bps:
        return jsonify({'status': False, 'message': 'app disabled: %s' % a})

    t = r.args.get('target')
    return MetaFile.dd(':'.join((a, e)) if e else a, t)


@app_.route('/<string:a>:<string:e>/upload', methods=['post'], endpoint='e_up')
@app_.route('/<string:a>/upload', methods=['post'], defaults={'e': ''}, endpoint='up')
@ind.wex
@ind.rtk
def _(a, e):
    target = r.form.get('target', '')
    file = r.files.get('file')
    return jsonify(MetaFile.up(':'.join((a, e)) if e else a, target, file))


@app_.route('/<string:a>:<string:e>/resize', methods=['get'], endpoint='e_rs')
@app_.route('/<string:a>/resize', methods=['get'], defaults={'e': ''}, endpoint='rs')
@ind.wex
@ind.rtk
def _(a, e):
    target = r.args.get('target', '')
    lt = r.args.get('lt')
    rb = r.args.get('rb')
    co = r.args.get('co')
    return jsonify(MetaFile.rs(':'.join((a, e)) if e else a, target, lt, rb, co))


@app_.route('/<string:a>:<string:e>/json', methods=['get'], endpoint='e_js')
@app_.route('/<string:a>/json', methods=['get'], defaults={'e': ''}, endpoint='js')
@ind.wex
@ind.rtk
def _(a, e):
    target = r.args.get('target', '')
    return jsonify(MetaFile.js(':'.join((a, e)) if e else a, target))


@app_.route('/restart', methods=['get'], endpoint='restart')
@ind.wex
@ind.rtk
@ind.c4s(log=True)
def _():
    _bps = [bp for bp in cons.Apps.apps.keys() if r.args.get(bp, 'false').lower() == 'true']
    print('restart:', _bps)
    ins.ins_que.put(_bps)
    return jsonify({'status': True, 'message': ', '.join(_bps)})


class Hook4Scanner(object):
    def __init__(self, app):
        self.app = app
        self.logger = logging.getLogger('Hook4Scanner')
        self.logger.setLevel('INFO')
        handler = logging.FileHandler('Hook4Scanner.log', encoding='UTF-8')
        handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
        self.logger.addHandler(handler)

    def __call__(self, environ, start_response):
        protocol = environ.get('SERVER_PROTOCOL').upper()
        method = environ.get('REQUEST_METHOD').upper()
        addr = environ.get('REMOTE_ADDR')
        uri = environ.get('REQUEST_URI')
        if method in ('OPTIONS', 'CONNECT', 'HEAD', 'TRACE') or protocol not in ('HTTP/1.1',):
            from werkzeug.wrappers import Response
            self.logger.log(logging.ERROR, '%s %s %s %s' % (protocol, method, addr, uri))

            return Response(b'', status=403)(environ, start_response)

        def do_start_response(status, headers, exc_info=None):
            if status.startswith('404') or status.startswith('400'):
                self.logger.log(logging.ERROR, '%s %s %s %s %s' % (protocol, method, addr, uri, status))
            return start_response(status, headers, exc_info)

        return self.app(environ, do_start_response)


app_.wsgi_app = Hook4Scanner(app_.wsgi_app)
