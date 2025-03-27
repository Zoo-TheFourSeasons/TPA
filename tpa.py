# coding=utf-8
import importlib
import argparse

from app import app_, socket_io
import ins
import cons


if __name__ == '__main__':
    bp_all = list(cons.Apps.apps.keys())

    parser = argparse.ArgumentParser()
    parser.add_argument('--ip', help='ip: 0.0.0.0', type=str, default='0.0.0.0')
    parser.add_argument('--bp', help='all: %s' % bp_all, type=str, default=','.join(cons.APPS_DEFAULT))
    parser.add_argument('--port', help='port: 80', type=int, default=80)

    ars = parser.parse_args()

    # register bp
    ins.ins_bps = bp_all if ars.bp == cons.APP_ALL else ars.bp.split(',')
    bps_ins = (importlib.import_module(b + '.bp') for b in ins.ins_bps if b in cons.Apps.apps)

    [app_.register_blueprint(i.bp) for i in bps_ins]

    bfs_ins = (importlib.import_module(b + '.before') for b in ins.ins_bps if b in cons.Apps.apps)
    for bf in bfs_ins:
        for f in bf.inits:
            f()

    print('bps:', ins.ins_bps)
    try:
        socket_io.run(app_, host=ars.ip, port=int(ars.port), use_reloader=False, allow_unsafe_werkzeug=True)
    except TypeError as _:
        socket_io.run(app_, host=ars.ip, port=int(ars.port), use_reloader=False)
