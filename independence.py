# -*- coding: utf-8 -*-
import traceback
import json
import time
from functools import wraps
from types import FunctionType

from flask import request, make_response, redirect, url_for, jsonify

import cons
import ins


def timer(func):
    @wraps(func)
    def function_timer(*args, **kwargs):
        rel_start = time.time()
        cpu_start = time.perf_counter()
        result = func(*args, **kwargs)
        rel_cost = time.time() - rel_start
        cpu_cost = time.perf_counter() - cpu_start

        if '__code__' in dir(func):
            file_ = func.__getattribute__('__code__').co_filename
        else:
            file_ = 'builtin_function_or_method'

        s = ' '.join((file_ + '.' + func.__name__, str(rel_cost), str(cpu_cost)))
        print(s)
        return result

    return function_timer


def wraps_data_in_get(data: dict):
    tmp = {}
    for k, v in data.items():
        if isinstance(v, (dict, list, tuple)):
            tmp[k] = json.dumps(v)
            continue
        tmp[k] = v
    return tmp


def decorate_meta(decorator):
    class MetaDecorate(type):
        def __new__(mcs, class_name, supers, class_dict):
            for attr, attr_val in class_dict.items():
                if type(attr_val) is FunctionType:
                    class_dict[attr] = decorator(attr_val)
            return type.__new__(mcs, class_name, supers, class_dict)

    return MetaDecorate


def rtk(func):
    # require header for tk
    def warp(*args, **kwargs):
        def _warp():
            # require user
            if cons.APP_USR in ins.ins_bps:
                tk = request.args.get('tk', '')
                if not tk or tk not in ins.ins_tokens:
                    if 'json' in str(request.accept_mimetypes):
                        return make_response({'status': False, 'message': 'login required'}, 403, None)
                    # n = request.url.replace(request.url_root, '').replace(tk, '')
                    # return redirect(url_for('login', next=n))
                    return redirect(url_for('login'))
            # require bps
            app = request.view_args.get('app')
            if app and app not in ins.ins_bps:
                return redirect(url_for('login'))
            return func(*args, **kwargs)
        return _warp()
    return warp


def wrj(func):
    # warp requests for json
    def warp(*args, **kwargs):
        def _warp():
            try:
                rsp = func(*args, **kwargs)
            except Exception as e:
                return {'message': 'failed in requests: %s' % e}
            if not str(rsp.status_code).startswith('20'):
                r = {'status_code': rsp.status_code, 'rsp': rsp.text}
                print(rsp.status_code, r)
                return r
            try:
                r = rsp.json()
            except Exception as _:
                print(rsp.status_code, 'rsp text:', rsp.text)
                return rsp
            return r

        return _warp()

    return warp


def wex(func):
    # warp exceptions
    def warp(*args, **kwargs):
        def _warp():
            try:
                return func(*args, **kwargs)
            except Exception as e:
                print(traceback.format_exc())
                return jsonify({'status': False, 'message': repr(e)})
        return _warp()
    return warp


def vda(a):
    if a and a not in ins.ins_bps:
        raise ValueError('app disabled: %s' % a)


TimerMeta = decorate_meta(timer)
