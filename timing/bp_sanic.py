# -*- coding: utf-8 -*-
from sanic import Blueprint, request
from sanic import json as jsonify

from timing.assistant import TimingHelper as Ass
from cons import APP_TIM as APP
import independence_sanic as ind

bp = Blueprint(APP, __name__)


@bp.route('/timing/update', methods=['get'], endpoint='touch')
@ind.wex
@ind.rtk
def update():
    ind.vda(APP)

    text = request.args.get('text')
    target = request.args.get('target')
    return jsonify(Ass.update(text, APP, target))


@bp.route('/timing/execute', methods=['get'], defaults={'func': Ass.execute, 'status': None}, endpoint='execute')
@bp.route('/timing/off', methods=['get'], defaults={'func': Ass.status, 'status': False}, endpoint='off')
@bp.route('/timing/on', methods=['get'], defaults={'func': Ass.status, 'status': True}, endpoint='on')
@ind.wex
@ind.rtk
def execute(func, status):
    ind.vda(APP)

    return jsonify(func(APP, request.args.get('target'), status))
