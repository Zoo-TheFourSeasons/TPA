# -*- coding: utf-8 -*-
"""app
"""
import os

from sanic import Sanic
from sanic import json as jf
from sanic import request as r
from sanic import redirect
# from apscheduler import events
# from flask import Flask
# from flask_socketio import SocketIO
# from flask_apscheduler import APScheduler
# from flask import jsonify as jf
# from flask import render_template as rt
# from flask import request as r
# from flask import redirect, url_for

import independence_sanic as ind
import ins
import cons
from base import MetaFile


def create_app():
    """create app
    """
    # _app = Sanic(__name__, template_folder='bs5/templates', static_folder='bs5/static')
    _app = Sanic(__name__)
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
# scheduler = APScheduler()
# scheduler.init_app(app_)
# scheduler.start()
# scheduler.add_listener(job_missed, events.EVENT_JOB_MISSED)
# scheduler.add_listener(job_error, events.EVENT_JOB_ERROR)
# scheduler.add_listener(job_executed, events.EVENT_JOB_EXECUTED)
# scheduler.add_listener(job_added, events.EVENT_JOB_ADDED)
# scheduler.add_listener(job_removed, events.EVENT_JOB_REMOVED)
# scheduler.add_listener(job_submitted, events.EVENT_JOB_SUBMITTED)

# init websocket
# socket_io = SocketIO(
#     app_,
#     async_mode='threading',
#     ping_timeout=6000,
#     ping_interval=60
# )


@app_.route('/login', methods=['get'], defaults={'f': 'login'}, endpoint='login')
@app_.route('/register', defaults={'f': 'register'}, methods=['get'], endpoint='register')
@ind.wex
@ind.c4s(log=True)
def _(f):
    if cons.APP_USR not in ins.ins_bps:
        return redirect(app_.url_for('home'))
    return ind.rt('%s.html' % f, **{'_bps': ins.ins_bps})


@app_.route('/', methods=['get'], defaults={'a': '', 'e': '', 'f': ''}, endpoint='home')
@app_.route('/webs/<string:f>', defaults={'a': '', 'e': ''}, methods=['get'], endpoint='f')
@app_.route('/webs/<string:a>/<string:f>', methods=['get'], defaults={'e': ''}, endpoint='a')
@app_.route('/webs/<string:a>:<string:e>/<string:f>', methods=['get'], endpoint='e')
@ind.wex
@ind.rtk
@ind.c4s(log=True)
def _(a, e, f):
    if a and a not in ins.ins_bps:
        return jf({'status': False, 'message': 'app disabled: %s' % a})

    _bps = ins.ins_bps
    if not a and not e:
        app = r.args.get('app', '')
        ae = app.split(':')
        edp = 'home' if not app else ae[1] if ':' in app else ae[0]
    else:
        edp = a if not e else e

    if not a and not f:
        return ind.rt('home.html', **locals())
    if not a:
        return ind.rt('%s.html' % f, **locals())
    if not e:
        return ind.rt('%s/%s.html' % (a, f), **locals())
    return ind.rt('%s/%s/%s.html' % (a, e, f), **locals())


@app_.route('/<string:a>:<string:e>/index', methods=['get'], endpoint='e_index')
@app_.route('/<string:a>/index', methods=['get'], defaults={'e': ''}, endpoint='index')
@ind.wex
@ind.rtk
@ind.c4s(log=True)
def _(a, e):
    if a not in ins.ins_bps:
        return jf({'status': False, 'message': 'app disabled: %s' % a})

    t = r.args.get('target', '')
    if a in (cons.APP_ZOO, cons.APP_SEC, cons.APP_ENC) or e == cons.EDP_DF:
        suffix = None
    else:
        suffix = '.' + e if e else a
    if a == cons.APP_TIM:
        from timing.assistant import TimingHelper as Ass
        f = Ass.ldr
    elif cons.APP_STA in ins.ins_bps:
        from star.assistant import StarHelper as Ass
        f = Ass.ldr
    else:
        f = MetaFile.ldr
    return jf(f(':'.join((a, e)) if e else a, t, r.args, suffix))


@app_.route('/<string:a>:<string:e>/delete', methods=['get'], endpoint='e_delete')
@app_.route('/<string:a>/delete', methods=['get'], defaults={'e': ''}, endpoint='delete')
@ind.wex
@ind.rtk
@ind.c4s(log=True)
def _(a, e):
    if a not in ins.ins_bps:
        return jf({'status': False, 'message': 'app disabled: %s' % a})
    if a == cons.APP_TIM:
        from timing.assistant import TimingHelper as Ass
        f = Ass.remove
    else:
        f = MetaFile.de
    return jf(f(':'.join((a, e)) if e else a, r.args.get('target')))


@app_.route('/<string:a>:<string:e>/touch', methods=['get'], endpoint='e_touch')
@app_.route('/<string:a>/touch', methods=['get'], defaults={'e': ''}, endpoint='touch')
@ind.wex
@ind.rtk
@ind.c4s(log=True)
def _(a, e):
    if a not in ins.ins_bps:
        return jf({'status': False, 'message': 'app disabled: %s' % a})

    t = r.args.get('target')
    if a == cons.APP_TIM:
        from timing.assistant import TimingHelper as Ass
        f = Ass.update if os.path.exists(Ass.aep(a, e, t)) else MetaFile.th
    else:
        f = MetaFile.th

    text = r.args.get('text')
    return jf(f(text, ':'.join((a, e)) if e else a, t))


@app_.route('/<string:a>:<string:e>/mkdir', methods=['get'], endpoint='e_mkdir')
@app_.route('/<string:a>/mkdir', methods=['get'], defaults={'e': ''}, endpoint='mkdir')
@ind.wex
@ind.rtk
@ind.c4s(log=True)
def _(a, e):
    if a not in ins.ins_bps:
        return jf({'status': False, 'message': 'app disabled: %s' % a})

    t = r.args.get('target')
    if '&' in t or ',' in t:
        return jf({'status': False, 'message': 'target can not contain special char: &,'})
    return jf(MetaFile.mdr(':'.join((a, e)) if e else a, t))


@app_.route('/<string:a>:<string:e>/view', methods=['get'], endpoint='e_view')
@app_.route('/<string:a>/view', methods=['get'], defaults={'e': ''}, endpoint='view')
@ind.wex
@ind.rtk
@ind.c4s(log=True)
def _(a, e):
    if a not in ins.ins_bps:
        return jf({'status': False, 'message': 'app disabled: %s' % a})

    t = r.args.get('target')
    return jf(MetaFile.vw(':'.join((a, e)) if e else a, t, r.args))


@app_.route('/<string:a>:<string:e>/download', methods=['get'], endpoint='e_dd')
@app_.route('/<string:a>/download', methods=['get'], defaults={'e': ''}, endpoint='dd')
@ind.wex
@ind.rtk
@ind.c4s(log=True)
def _(a, e):
    if a not in ins.ins_bps:
        return jf({'status': False, 'message': 'app disabled: %s' % a})

    t = r.args.get('target')
    return MetaFile.dd(':'.join((a, e)) if e else a, t)


@app_.route('/restart', methods=['get'], endpoint='restart')
@ind.wex
@ind.rtk
@ind.c4s(log=True)
def _():
    _bps = [bp for bp in cons.Apps.apps.keys() if r.args.get(bp, 'false').lower() == 'true']
    print('restart:', _bps)
    ins.ins_que.put(_bps)
    return jf({'status': True, 'message': ', '.join(_bps)})
