# coding=utf-8
import importlib
from app_sanic import app
import cons
import ins

ins.ins_bps = list(cons.Apps.apps.keys())
bps_ins = (importlib.import_module(b + '.bp_sanic') for b in ins.ins_bps)

[app.blueprint(i.bp) for i in bps_ins]

if __name__ == '__main__':
    app.run('0.0.0.0', port=80, debug=True, access_log=True, workers=1)
