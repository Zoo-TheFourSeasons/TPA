# -*- coding: utf-8 -*-
import os

from sanic import redirect
from sanic import Blueprint
from sanic.response import json as jsonify

from base import MetaFile
from sc_app import app
import independence_sanic as ind
import cons
import ins


bp = Blueprint('curd')


@bp.get('/', name='home')
@ind.c4s(log=True)
async def _(request):
    _bps = ins.ins_bps
    a = request.args.get('app', '')
    ae = a.split(':')
    edp = 'home' if not a else ae[1] if ':' in a else ae[0]
    return ind.rt('home.html', **locals())


@bp.get('/login', name='login')
@ind.c4s(log=True)
async def _(request):
    if cons.APP_USR not in ins.ins_bps:
        return redirect(app.url_for('home'))
    return ind.rt('login.html', **{'_bps': ins.ins_bps})


@bp.get('/register', name='register')
@ind.c4s(log=True)
async def _(request):
    if cons.APP_USR not in ins.ins_bps:
        return redirect(app.url_for('home'))
    return ind.rt('register.html', **{'_bps': ins.ins_bps})


@bp.get('/webs/<ae:str>/index', name='page')
@ind.c4s(log=True)
async def _(request, ae):
    a, e = ae.split(':') if ':' in ae else (ae, '')

    if a and a not in ins.ins_bps:
        return jsonify({'status': False, 'message': 'app disabled: %s' % a})

    _bps = ins.ins_bps
    if not a and not e:
        a = request.args.get('app', '')
        ae = a.split(':')
        edp = 'home' if not a else ae[1] if ':' in a else ae[0]
    else:
        edp = a if not e else e
    if not a:
        return ind.rt('index.html', **locals())
    if not e:
        return ind.rt('%s/index.html' % a, **locals())
    return ind.rt('%s/%s/index.html' % (a, e), **locals())


@bp.get('/<ae:str>/index', name='index')
@ind.c4s(log=True)
async def _(request, ae):
    a, e = ae.split(':') if ':' in ae else (ae, '')
    if a not in ins.ins_bps:
        return jsonify({'status': False, 'message': 'app disabled: %s' % a})

    t = request.args.get('target', '')
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
    return jsonify(f(':'.join((a, e)) if e else a, t, request.args, suffix))


@bp.get('/<ae:str>/delete', name='delete')
@ind.c4s(log=True)
async def _(request, ae):
    a, e = ae.split(':') if ':' in ae else (ae, '')
    if a not in ins.ins_bps:
        return jsonify({'status': False, 'message': 'app disabled: %s' % a})
    if a == cons.APP_TIM:
        from timing.assistant import TimingHelper as Ass
        f = Ass.remove
    else:
        f = MetaFile.de
    return jsonify(f(':'.join((a, e)) if e else a, request.args.get('target')))


@bp.get('/<ae:str>/touch', name='touch')
@ind.c4s(log=True)
async def _(request, ae):
    a, e = ae.split(':') if ':' in ae else (ae, '')
    if a not in ins.ins_bps:
        return jsonify({'status': False, 'message': 'app disabled: %s' % a})

    t = request.args.get('target')
    if a == cons.APP_TIM:
        from timing.assistant import TimingHelper as Ass
        f = Ass.update if os.path.exists(Ass.aep(a, e, t)) else MetaFile.th
    else:
        f = MetaFile.th

    text = request.args.get('text')
    return jsonify(f(text, ':'.join((a, e)) if e else a, t))


@bp.get('/<ae:str>/mkdir', name='mkdir')
@ind.c4s(log=True)
async def _(request, ae):
    a, e = ae.split(':') if ':' in ae else (ae, '')
    if a not in ins.ins_bps:
        return jsonify({'status': False, 'message': 'app disabled: %s' % a})

    t = request.args.get('target')
    if '&' in t or ',' in t:
        return jsonify({'status': False, 'message': 'target can not contain special char: &,'})
    return jsonify(MetaFile.mdr(':'.join((a, e)) if e else a, t))


@bp.get('/<ae:str>/view', name='view')
@ind.c4s(log=True)
async def _(request, ae):
    a, e = ae.split(':') if ':' in ae else (ae, '')
    if a not in ins.ins_bps:
        return jsonify({'status': False, 'message': 'app disabled: %s' % a})

    t = request.args.get('target')
    return jsonify(MetaFile.vw(':'.join((a, e)) if e else a, t, request.args))


@bp.get('/<ae:str>/download', name='download')
@ind.c4s(log=True)
async def _(request, ae):
    a, e = ae.split(':') if ':' in ae else (ae, '')
    if a not in ins.ins_bps:
        return jsonify({'status': False, 'message': 'app disabled: %s' % a})

    t = request.args.get('target')
    return MetaFile.dd(':'.join((a, e)) if e else a, t)
