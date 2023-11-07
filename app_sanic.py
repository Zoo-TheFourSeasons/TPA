# -*- coding: utf-8 -*-
"""app
"""
import os

from sanic import Sanic
from sanic import json as jsonify
from sanic import redirect

import independence_sanic as ind
import ins
import cons
from base import MetaFile


app = Sanic(__name__)
app.static('/static', 'bs5/static')


@app.get('/', name='home')
async def _(request):
    _bps = ins.ins_bps
    a = request.args.get('app', '')
    ae = a.split(':')
    edp = 'home' if not a else ae[1] if ':' in a else ae[0]
    return ind.rt('home.html', **locals())


@app.get('/login', name='login')
async def _(request):
    if cons.APP_USR not in ins.ins_bps:
        return redirect(app.url_for('home'))
    return ind.rt('login.html', **{'_bps': ins.ins_bps})


@app.get('/register', name='register')
async def _(request):
    if cons.APP_USR not in ins.ins_bps:
        return redirect(app.url_for('home'))
    return ind.rt('register.html', **{'_bps': ins.ins_bps})


@app.get('/webs/<ae:str>/index', name='page')
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


@app.get('/<ae:str>/index', name='index')
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


@app.get('/<ae:str>/delete', name='delete')
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


@app.get('/<ae:str>/touch', name='touch')
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


@app.get('/<ae:str>/mkdir', name='mkdir')
async def _(request, ae):
    a, e = ae.split(':') if ':' in ae else (ae, '')
    if a not in ins.ins_bps:
        return jsonify({'status': False, 'message': 'app disabled: %s' % a})

    t = request.args.get('target')
    if '&' in t or ',' in t:
        return jsonify({'status': False, 'message': 'target can not contain special char: &,'})
    return jsonify(MetaFile.mdr(':'.join((a, e)) if e else a, t))


@app.get('/<ae:str>/view', name='view')
async def _(request, ae):
    a, e = ae.split(':') if ':' in ae else (ae, '')
    if a not in ins.ins_bps:
        return jsonify({'status': False, 'message': 'app disabled: %s' % a})

    t = request.args.get('target')
    return jsonify(MetaFile.vw(':'.join((a, e)) if e else a, t, request.args))


@app.get('/<ae:str>/download', name='download')
async def _(request, ae):
    a, e = ae.split(':') if ':' in ae else (ae, '')
    if a not in ins.ins_bps:
        return jsonify({'status': False, 'message': 'app disabled: %s' % a})

    t = request.args.get('target')
    return MetaFile.dd(':'.join((a, e)) if e else a, t)
