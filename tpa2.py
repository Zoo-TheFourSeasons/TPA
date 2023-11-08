# coding=utf-8
from sc_app import app
import cons
import ins
from curd.sc_bp import bp as bp_curd

ins.ins_bps = list(cons.Apps.apps.keys())
app.blueprint(bp_curd)

if __name__ == '__main__':
    app.run('0.0.0.0', port=80, access_log=True, workers=4)
