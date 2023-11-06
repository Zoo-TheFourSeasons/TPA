# coding=utf-8
import importlib

from app_sanic import app_
import ins
import cons

if __name__ == '__main__':
    # register bp
    ins.ins_bps = list(cons.Apps.apps.keys())
    bps_ins = (importlib.import_module(b + '_sanic.bp') for b in ins.ins_bps if b in cons.Apps.apps)
    bfs_ins = (importlib.import_module(b + '_sanic.before') for b in ins.ins_bps if b in cons.Apps.apps)
    [app_.register_blueprint(i.bp) for i in bps_ins]
    [app_.before_first_request_funcs.extend(i.inits) for i in bfs_ins]
    print('bps:', ins.ins_bps)

    app_.run(host='0.0.0.0', port=80, use_reloader=False)
