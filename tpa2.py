# coding=utf-8
from sc_app import app
import cons
import ins
from curd.pbp import bp as bp_curd
from dsp.pbp import bp as bp_dsp
from en_decrypt.pbp import bp as bp_en_decrypt
from finansis.pbp import bp as bp_finansis
from history.pbp import bp as bp_history
from know.pbp import bp as bp_know
from security.pbp import bp as bp_security
from spatiotemporal.pbp import bp as bp_spatiotemporal
from squirrel.pbp import bp as bp_squirrel
from star.pbp import bp as bp_star
from timing.pbp import bp as bp_timing
from user.pbp import bp as bp_user
from zoo.pbp import bp as bp_zoo

ins.ins_bps = list(cons.Apps.apps.keys())
app.blueprint(bp_curd)
app.blueprint(bp_curd)
app.blueprint(bp_dsp)
app.blueprint(bp_en_decrypt)
app.blueprint(bp_finansis)
app.blueprint(bp_history)
app.blueprint(bp_know)
app.blueprint(bp_security)
app.blueprint(bp_spatiotemporal)
app.blueprint(bp_squirrel)
app.blueprint(bp_star)
app.blueprint(bp_timing)
app.blueprint(bp_user)
app.blueprint(bp_zoo)

if __name__ == '__main__':
    app.run('0.0.0.0', port=80, access_log=True, workers=4)
