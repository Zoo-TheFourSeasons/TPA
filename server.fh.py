# coding=utf-8
import importlib
import argparse

from app import app_, socket_io
import cons
import ins


def app_launcher(args):
    print('app_launcher:', args.ip, args.port)
    bps = args.bps
    ins.ins_bps = list(cons.APPS_DEFAULT) if not bps else list(cons.Apps.apps.keys()) if bps == cons.APP_ALL else bps.split(',')
    bps_ins = (importlib.import_module(b + '.bp') for b in ins.ins_bps if b in cons.Apps.apps)
    bfs_ins = (importlib.import_module(b + '.before') for b in ins.ins_bps if b in cons.Apps.apps)
    [app_.register_blueprint(i.bp) for i in bps_ins]
    [app_.before_first_request_funcs.extend(i.inits) for i in bfs_ins]
    print('bps:', ins.ins_bps)

    socket_io.run(app_, host=args.ip, port=int(args.port), use_reloader=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--ip', help='ip', type=str, default='0.0.0.0')
    parser.add_argument('--port', help='port', type=int, default=9755)
    parser.add_argument('--bps', help='blueprints', type=str, default='')

    app_launcher(parser.parse_args())
