# -*- coding: utf-8 -*-
from sanic import Blueprint
from sanic.response import json as jsonify

from timing.assistant import TimingHelper as Ass
from cons import APP_TIM as APP
import independence_sanic as ind

bp = Blueprint(APP)


@bp.get('/timing/update', name='update')
@ind.wex
@ind.rtk
async def _(request):
    ind.vda(APP)

    text = request.args.get('text')
    target = request.args.get('target')
    return jsonify(Ass.update(text, APP, target))


@bp.get('/timing/execute', name='execute')
@ind.wex
@ind.rtk
async def _(request):
    ind.vda(APP)

    return jsonify(Ass.execute(APP, request.args.get('target'), None))


@bp.get('/timing/off', name='off')
@ind.wex
@ind.rtk
async def _(request):
    ind.vda(APP)

    return jsonify(Ass.status(APP, request.args.get('target'), False))


@bp.get('/timing/on', name='on')
@ind.wex
@ind.rtk
async def _(request):
    ind.vda(APP)

    return jsonify(Ass.status(APP, request.args.get('target'), True))
