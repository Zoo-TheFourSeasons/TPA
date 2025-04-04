# -*- coding: utf-8 -*-
import base64
import copy
import datetime
import html
import importlib
import json
import logging
import multiprocessing
from multiprocessing.dummy import Process
import os
import sys
import shutil
import subprocess
import time
import threading
import traceback
import uuid

import requests
import cv2
import numpy
import yaml
from flask_socketio import Namespace, join_room
from flask import send_from_directory

import ins
import cons
import independence
from cons import APP_SQU

ojn = os.path.join
oid = os.path.isdir
oif = os.path.isfile
odn = os.path.dirname
osp = os.path.split
oex = os.path.exists
oap = os.path.abspath

PATH_PROJECT = odn(oap(__file__))
logging.getLogger('paramiko.transport').setLevel(logging.CRITICAL)


def data_paging_for_pickle(request, _ins, key_name, exclude=None, fields=None):
    items = sorted(_ins.keys())
    if 'search' in request.args and request.args['search']:
        search = request.args['search']

        items_ = []
        if fields:
            for k in fields:
                for item in items:
                    v = _ins[item][k]
                    # print('v: ' + v + ' k: ' + k + ' search: ' + search)
                    if v == search:
                        items_.append(item)

            for item in items:
                if search in item and item not in items_:
                    items_.append(item)
        else:
            items_ = [item for item in items if search in item]
        items = items_

    # 按条件过滤
    if 'query' in request.args and request.args['query']:
        query = request.args['query']
        query = query.replace(' ', '')
        # 暂不支持or
        query_list = []
        for item in query.split('and'):
            if '>=' in item:
                operator = '>='
                ope = '__ge__'
            elif '<=' in item:
                operator = '<='
                ope = '__le__'
            elif '==' in item:
                operator = '=='
                ope = '__eq__'
            elif '!=' in item:
                operator = '!='
                ope = '__ne__'
            elif '>' in item:
                operator = '>'
                ope = '__gt__'
            elif '<' in item:
                operator = '<'
                ope = '__lt__'
            else:
                continue
            tmp = item.split(operator)
            if len(tmp) != 2:
                continue
            query_list.append((tmp[0], ope, tmp[1]))

        print(query_list)
        for name, stock in _ins.items():
            for item in query_list:
                field = item[0]
                operator = item[1]
                value = float(item[2])
                if field not in stock:
                    items.remove(name)
                    break
                if not stock[field].__getattribute__(operator)(value):
                    if name not in items:
                        break
                    items.remove(name)
                    break

    total = len(items)

    if 'sort' in request.args and 'order' in request.args:
        sort = request.args['sort']
        order = request.args['order']
        if sort and order:
            items_need_sort = (item for item in items if sort in _ins[item])
            items_cannot_sort = [item for item in items if sort not in _ins[item]]
            items_sort = ((item, _ins[item][sort]) for item in items_need_sort)
            if order == 'asc':
                items_sort = sorted(items_sort, key=lambda x: x[1])
            else:
                items_sort = sorted(items_sort, key=lambda x: x[1], reverse=True)
            items = [item[0] for item in items_sort] + items_cannot_sort

    if 'offset' in request.args and 'limit' in request.args:
        offset = request.args['offset']
        limit = request.args['limit']
        if offset and limit:
            items = items[int(offset): int(offset) + int(limit)]

    rows = []
    for item in items:
        temp = _ins[item]
        if exclude:
            for ex in exclude:
                temp.pop(ex, None)

        temp.update({key_name: item, 'id': item})
        rows.append(temp)
    return total, rows


# def fix_service_providers_in_neutron_conf(func):
#     def _wrapper(_ins, _command, node, stacks):
#         _file = _command[cons.F_FILE]
#         _file = _file.strip()
#
#         if _file.endswith('neutron.conf'):
#             section_name = 'service_providers'
#             section_name__ = ''.join(('[', section_name, ']'))
#
#             # get service_providers in yaml
#             _data = _command[cons.O_CONF]
#             service_providers_yaml = _data.pop(section_name, {})
#             service_providers_yaml = ['='.join((k, v)) for k, v in service_providers_yaml.items()]
#
#             # get service_providers in conf
#             service_providers_conf = []
#             with open(_file, 'r') as f:
#                 content = f.read()
#                 content = '\n' + content.replace(' ', '')
#                 items = content.split('\n' + section_name__)
#                 # agent.echo({'print': 'self.FIELD_DETAIL items: %s' % json.dumps(items)})
#             if len(items) == 2:
#                 head = items[0]
#                 service_providers_str = items[1]
#                 tail = '\n'
#                 if '[' in service_providers_str:
#                     tail += service_providers_str[service_providers_str.find('['):]
#                     service_providers_str = service_providers_str[:service_providers_str.find('[')]
#                 service_providers_conf = service_providers_str.split('\n')
#                 # truncation
#                 with open(_file, 'w') as f:
#                     f.write(head + tail)
#
#             v = func(_ins, _command, node, stacks)
#             service_providers = list(set(service_providers_yaml + service_providers_conf))
#             with open(_file, 'a') as f:
#                 f.write(section_name__ + '\n' + '\n'.join(service_providers))
#             return v
#
#         v = func(_ins, _command, node, stacks)
#         return v
#
#     return _wrapper


class MetaProcess(multiprocessing.Process):

    def __init__(self, func, daemon=False, *args, **kwargs):
        super(MetaProcess, self).__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.daemon = daemon

    def run(self) -> None:
        self.func(*self.args, **self.kwargs)


class MetaDummyProcess(Process):

    def __init__(self, func, *args, **kwargs):
        super(MetaDummyProcess, self).__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs

    def start(self) -> None:
        self.func(*self.args, **self.kwargs)


class MetaFile(object):

    def __init__(self, ns=None, afp=None):
        self.debug = False
        self.ns = ns
        self.afp = afp
        self.task_id = None
        self.current_his = None

    @staticmethod
    def __sort(x):
        tmp = []
        for ix in x:
            if ix.isnumeric():
                tmp.append(ix)
            else:
                if tmp:
                    break
        try:
            v = int(''.join(tmp))
        except:
            v = id(''.join(tmp))
        return v

    @staticmethod
    def is_pic(fn):
        return fn.lower().split('.')[-1] in ('jpg', 'jpeg', 'png', 'webp')

    @staticmethod
    def is_vid(fn):
        return fn.lower().split('.')[-1] in ('mp4', 'avi', 'mkv', 'webm', 'mkv', 'ogv')

    @staticmethod
    def is_aud(fn):
        return fn.lower().split('.')[-1] in ('wav', 'ogg', 'mp3')

    @staticmethod
    def is_html(fn):
        return fn.lower().split('.')[-1] in ('html', )

    @staticmethod
    def is_yml(fn):
        return fn.lower().split('.')[-1] in ('yml', )

    @staticmethod
    def is_json(fn):
        return fn.lower().split('.')[-1] in ('json', )

    @staticmethod
    def get_tps(tps, func):
        if isinstance(tps, str) and os.path.isdir(tps):
            _tps = [os.path.join(r, fn) for r, d, fs in os.walk(tps) for fn in fs if func(fn)]
        else:
            _tps = []
            for t in tps:
                if os.path.isdir(t):
                    _tps += [os.path.join(r, fn) for r, d, fs in os.walk(t) for fn in fs if func(fn)]
                else:
                    _tps.append(t)
        return _tps

    @staticmethod
    def is_not_wav(fn):
        return fn.lower().split('.')[-1] not in ('wav', )

    @staticmethod
    def is_xls(fn):
        return fn.lower().split('.')[-1] in ('xlsx', 'xls', )

    @staticmethod
    def ly(t):
        if not oex(t):
            raise FileNotFoundError('ly error, file not exist: %s' % t)
        with open(t, 'r', encoding='utf-8') as f:
            try:
                data = yaml.safe_load(f.read())
            except Exception as e:
                raise ValueError('ly error: %s, e: %s' % (t, e))
        return data

    @staticmethod
    def dy(t, data):
        with open(t, 'w', encoding='utf-8') as f:
            try:
                yaml.safe_dump(data, f)
            except Exception as e:
                raise ValueError('dy error: %s, e: %s' % (t, e))

    def print(self, pt, wt: dict = None, nolog: bool = False, mix: dict = None, room=None):
        if isinstance(pt, (dict, list, tuple)):
            try:
                pt = json.dumps(pt, default=str, indent=2)
            except Exception as err:
                pt = json.dumps({'error': str(err), 'pt': str(pt)}, indent=2)
        else:
            pt = str(pt)
        if mix:
            for k, v in mix.items():
                if k in pt:
                    pt = pt.replace(k, v)
        afp = self.ins.afp if 'ins' in self.__dict__ else self.afp
        room = room if room else afp
        if isinstance(self, MetaWebSocket):
            self.emit('his', data=html.escape(pt) + '\n', room=room)
        elif 'ns' in self.__dict__ and isinstance(self.ns, MetaWebSocket):
            self.ns.emit('his', data=html.escape(pt) + '\n', room=room)
        elif 'ins' in self.__dict__ and isinstance(self.ins.ns, MetaWebSocket):
            self.ins.ns.emit('his', data=html.escape(pt) + '\n', room=room)

        if 'current_his' in self.__dict__ and self.current_his:
            current_his = self.current_his
        elif 'ins' in self.__dict__ and 'current_his' in self.ins.__dict__:
            current_his = self.ins.current_his
        else:
            current_his = None
        if not current_his:
            return
        if nolog:
            wt = 'NOLOG IS True'
        else:
            if wt is not None:
                if isinstance(wt, (dict, list, tuple)):
                    try:
                        wt = json.dumps(wt, default=str, indent=2)
                    except Exception as err:
                        wt = json.dumps({'error': str(err), 'wt': str(wt)}, indent=2)
                else:
                    wt = str(wt)
            else:
                wt = pt
            if mix:
                for k, v in mix.items():
                    if k in wt:
                        wt = wt.replace(k, v)
        with open(current_his, 'a', encoding='utf-8') as file:
            file.write(wt + '\n')

    @staticmethod
    def __request_parser_args(args_r):
        if not args_r:
            return None, None, None, None, None
        args = {}
        # fix
        for k, v in args_r.items():
            args[k] = v[0] if isinstance(v, list) else v
        search = args['search'] if 'search' in args and args['search'] else None
        sort = args['sort'] if 'sort' in args and args['sort'] else None
        order = args['order'] if 'order' in args and args['order'] else None
        offset = int(args['offset']) if 'offset' in args and args['offset'] else None
        limit = int(args['limit']) if 'limit' in args and args['limit'] else None
        return search, sort, order, offset, limit

    @classmethod
    def view_img(cls, t):
        with open(t, 'rb') as f:
            b64 = 'data:;base64,' + str(base64.b64encode(f.read()))[2:-1]
        h, w = cv2.imread(t).shape[:2]
        return {'status': True, 'rows': b64, 'is_image': True,
                'type': 'img', 'w': w, 'h': h}

    @classmethod
    def __view_txt(cls, t):
        size = os.path.getsize(t) / 1024.0
        if size > 2048:
            size = round(size / 1024.0, 1)
            if size > 20:
                return {'status': False, 'message': 'size: %s M' % size, 'is_image': False, 'type': 'txt'}
        with open(t) as f:
            return {'status': True, 'rows': f.read(), 'is_image': False, 'type': 'txt'}

    @classmethod
    def __view_xls(cls, t, args_r, rounds=None):
        import pandas

        stat = os.stat(t)
        mt = stat.st_mtime

        if t not in ins.ins_xls_cache:
            # add in cache
            ins.ins_xls_cache[t] = {
                'df': pandas.read_excel(t),
                'st_mtime': mt
            }
            print('add ins_dfs_cache: %s' % t)
        else:
            # update cache
            if mt > ins.ins_xls_cache[t]['st_mtime']:
                ins.ins_xls_cache[t] = {
                    'df': pandas.read_excel(t),
                    'st_mtime': mt
                }
                print('update ins_dfs_cache: %s' % t)
        df = ins.ins_xls_cache[t]['df']
        _, _, _, offset, limit = cls.__request_parser_args(args_r)

        rows = []
        for i, _row in df.iterrows():
            if offset and i + 2 < offset:
                continue
            if limit and i + 2 > offset + limit:
                break
            tmp = {}
            for ii, col in enumerate(df.columns):
                value = _row[ii]
                if pandas.isna(value):
                    # NaN
                    tmp[col] = 'NaN'
                    continue
                if rounds:
                    # with rounds
                    for rd, keys in rounds.items():
                        if col not in keys:
                            continue
                        if rd < 1:
                            value = round(value, len(str(rd)) - 2)
                        else:
                            value = round(value / rd, 3) if value else value
                tmp[col] = str(value)
            rows.append(tmp)
        columns = [{'title': c, 'field': c, 'sortable': True, 'switchable': True} for c in df.columns]
        return {'status': True, 'rows': rows, 'total': df.shape[0], 'columns': columns, 'type': 'xls'}

    @classmethod
    def a_afp(cls, afp):
        # app data file path
        # afp = 'timing,ENCRYPT.tim'
        app, dfp = afp.split(',')
        return cls.a_dfp(app, dfp)

    @classmethod
    def a_dfp(cls, app, target):
        # app data file path
        # app = 'star'
        # target = 'STARS.sta'
        ap = cls.a_ddp(app)
        fp = ojn(ap, target)
        if not oap(fp).startswith(ap):
            raise ValueError('unknown target: %s' % target)
        # fp = '/home/zin/Desktop/_Y/TPA/star/data/STARS.sta'
        return fp

    @classmethod
    def aep(cls, app, edp, target):
        return cls.a_afp(':'.join((app, edp)) if edp else app + ',' + target)

    @staticmethod
    def a_ddp(a: str):
        # a: app:edp
        # app data dir path
        # a = 'timing'
        a, e = a.split(':') if ':' in a else (a, None)
        if a not in cons.Apps.apps:
            raise ValueError('unknown app: %s' % a)
        if a in (cons.APP_ENC, cons.APP_ZOO):
            return odn(PATH_PROJECT)
        if a in (cons.APP_MED, ):
            return '/file/data'
        dp = ojn(ojn(PATH_PROJECT, a), 'data')
        dp = dp if not e else ojn(dp, e)
        # dp = '/home/zin/Desktop/_Y/TPA/timing/data'
        return dp

    @staticmethod
    def a_edp(a: str):
        # a: app:edp
        # return edp
        return a.split(':')[1] if ':' in a else a

    @classmethod
    def a_hdp(cls, a: str):
        # a: app:edp or edp
        edp = a.split(':')[1] if ':' in a else a
        return ojn(cls.a_ddp(cons.APP_HIS), edp)

    @classmethod
    @independence.timer
    def dd(cls, app: str, target: str):
        print('dd', app, target)
        fp = cls.a_dfp(app, target)
        fd, fn = os.path.split(fp)

        return send_from_directory(fd, fn, as_attachment=True)

        # v = cls.a_dfp(app, target)
        # _, fn = osp(v)
        # lw = target.lower()
        # # txt
        # fnd = '%s.%s.txt' % (fn, cls.tsp(ed=17))
        # # img xls
        # for end in ('.jpg', '.png', '.jpeg', '.webp', '.xlsx', '.xls'):
        #     if lw.endswith(end):
        #         fnd = fn
        #         break
        # with open(v, 'rb') as f:
        #     ctx = f.read()
        #
        # # for CN
        # from urllib.parse import quote
        #
        # response = independence.make_response_with_headers(ctx, {
        #     'Content-Type': 'application/octet-stream',
        #     'Content-Disposition': "attachment; filename*=utf-8''%s" % (quote(fnd))
        # })
        #
        # return response

    @classmethod
    @independence.timer
    def df(cls, u, fp):
        print(f'download: {u}, to: {fp}')
        with requests.get(u, stream=True) as r:
            r.raise_for_status()
            with open(fp, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

    @classmethod
    @independence.timer
    def up(cls, app: str, target: str, file):
        fp = os.path.join(cls.a_dfp(app, target), file.filename)
        if os.path.exists(fp):
            return
        file.save(fp)
        return {'status': True}

    @classmethod
    @independence.timer
    def rs(cls, app: str, target: str, lt: str, rb: str, o: str):
        fp = cls.a_dfp(app, target)
        if not os.path.exists(fp):
            return {'status': False, 'message': 'FILE NOT EXIST: %s' % fp}
        ox, oy = o.split(',')
        ox, oy = int(float(ox)), int(float(oy))
        ltx, lty = lt.split(',')
        rbx, rby = rb.split(',')
        ltx, lty = int(float(ltx)), int(float(lty))
        rbx, rby = int(float(rbx)), int(float(rby))

        hi = rby - lty
        wi = rbx - ltx
        if hi < 0 or wi < 0:
            return {'status': False, 'message': 'hi or wi < 0'}
        frame = cv2.imread(fp)
        h, w, _ = frame.shape
        canvas = numpy.zeros((hi, wi, 3), dtype=numpy.uint8)
        canvas[:hi, :wi] = frame[lty - oy: hi + lty - oy, ltx - ox: wi + ltx - ox]
        cv2.imwrite(fp, canvas)
        return {'status': True, 'b64': cls.view_img(fp)['rows']}

    @classmethod
    def ldr(cls, app: str, target: str, args_r: dict = None, suffix=None) -> dict:
        search, _, _, offset, limit = cls.__request_parser_args(args_r)

        def do(_files):
            i = 0
            r = []
            for _app, afp in _files:
                i += 1
                if offset and i <= offset:
                    continue
                if limit and i > offset + limit:
                    break
                _fp = cls.a_dfp(_app, afp)
                stat = os.stat(_fp)
                size = os.path.getsize(_fp) / 1024.0
                size = str(round(size / 1024.0, 1)) + 'M' if size > 2048 else str(round(size, 1)) + 'K'
                _, fn = osp(_fp)
                r.append({
                    'fn': fn,
                    'isdir': oid(_fp),
                    'ctime': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(stat.st_ctime)),
                    'mtime': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(stat.st_mtime)),
                    'size': size,
                    'app': _app,
                    'afp': afp,
                    'id': afp,
                    'video': cls.is_vid(fn),
                })
            return r

        if search is not None:
            # search
            files, total = cls.fs(app, target, search)
        else:
            fp = cls.a_dfp(app, target)
            files, total = [], 0
            if oex(fp) and oid(fp):
                files = [f for f in os.listdir(fp) if not f.startswith('.')]
                if suffix:
                    # to fix
                    files = [f for f in files if f.endswith(suffix) or oid(cls.a_dfp(app, ojn(target, f)))]
                files.sort(reverse=True)
                total = len(files)
                files = ((app, ojn(target, f)) for f in files)

        rows = do(files)
        # parents of the current path
        target = '/'.join((app, target + '/' if target else target))
        target_split = target.split('/')
        parents = [{'i': e, 'i_path': '/'.join(target_split[1:i + 1])} for i, e in enumerate(target_split)]
        return {'status': True, 'rows': rows, 'target': target, 'parents': parents, 'total': total, 'app': app}

    @classmethod
    @independence.timer
    def vw(cls, app: str, target: str, args_r: dict = None) -> dict:
        print('vw', app, target)
        v = cls.a_dfp(app, target)
        if not oex(v):
            return {'status': False, 'message': 'there is not exist: %s' % target, 'type': 'txt'}
        if not oif(v):
            return {'status': False, 'message': 'is not a file: %s' % target, 'type': 'txt'}
        fd, fn = osp(target)
        at = '/'.join((app, target))
        target_split = at.split('/')
        parents = [{'i': e, 'i_path': '/'.join(target_split[1:i + 1])} for i, e in enumerate(target_split)]
        pfn = {'parents': parents, 'fn': fn, 'app': app, 'parent': fd}
        # audio video
        if cls.is_aud(v) or cls.is_vid(v):
            # return cls.dd(app, target)
            rsp = {'status': True, 'rows': '/' + app + '/download?target=' + target , 'is_image': False, 'type': 'aud' if cls.is_aud(v) else 'vid'}
        # img
        elif cls.is_pic(v):
            rsp = cls.view_img(v)
        # xls
        elif cls.is_xls(v):
            rsp = cls.__view_xls(v, args_r)
        # txt
        else:
            try:
                rsp = cls.__view_txt(v)
            except Exception as e:
                rsp = {'status': False, 'message': 'unknown file: %s' % e, 'type': 'txt'}
        rsp.update(pfn)
        return rsp

    @classmethod
    @independence.timer
    def de(cls, app: str, files: str) -> dict:
        print('de', files, app)
        failed = []
        message = 'delete success'
        for fn in files.split(','):
            fp = cls.a_dfp(app, fn)
            try:
                if oid(fp):
                    shutil.rmtree(fp)
                else:
                    os.remove(fp)
            except Exception as e:
                failed.append(fp)
                message = 'failed in delete: %s' % e
        return {'status': False if failed else True, 'message': message}

    @classmethod
    @independence.timer
    def js(cls, app: str, target: str) -> dict:
        print('js', target, app)
        fp = cls.a_dfp(app, target)
        return json.load(open(fp, 'r'))

    @classmethod
    def __execute_sh(cls, fp):
        pass

    @classmethod
    def __execute_py(cls, fp):
        me = importlib.import_module(fp.replace(PATH_PROJECT, '').replace('/', '.')[1:-3])
        importlib.reload(me)
        f = getattr(me, 'run')
        cls.run_in_subprocess(f)

    @classmethod
    @independence.timer
    def ee(cls, files: str, app: str) -> dict:
        print('ee', files, app)
        failed = []
        message = 'execute success'

        for fn in files.split(','):
            fp = cls.a_dfp(app, fn)
            if oid(fp):
                continue
            try:
                if fp.endswith('sh'):
                    cls.__execute_sh(fp)
                elif fp.endswith('py'):
                    cls.__execute_py(fp)
            except Exception as e:
                failed.append(fn)
                # print(traceback.format_exc())
                message = 'failed in execute: %s' % e
        return {'status': False if failed else True, 'message': message}

    @classmethod
    def fs(cls, app, _, searches) -> tuple:
        # file search
        files = []

        def fs_a(fts, ft='a'):
            # app name
            if ft in fts and fts[ft]:
                v = fts[ft]
                if v == cons.APP_ALL:
                    v = [a for a in cons.Apps.apps.keys() if a not in (cons.APP_ZOO, cons.APP_ENC)]
                else:
                    v = v.split(' ')
                # filter 
                if ins.ins_bps:
                    v = [i for i in v if i in ins.ins_bps]
                apps = []
                [apps.extend(cons.Apps.apps.get(i)) for i in v]
                print('apps', apps)
                return apps
            return [app, ]

        def fs_d(fts, apps, ft='d'):
            # dir name contain
            if ft in fts and fts[ft]:
                v = fts[ft]
                v = v.split(' ')
                # for a in apps:
                #     for _d in v:
                #         for r, ds, _ in os.walk(cls.a_ddp(a)):
                #             for d in ds:
                #                 if _d.lower() in d.lower():
                #                     print(a, ojn(r, d))
                return ((a, ojn(r, d)) for a in apps for _d in v for r, ds, _ in os.walk(cls.a_ddp(a)) for d in ds if
                        _d.lower() in d.lower())
            return ((a, cls.a_ddp(a)) for a in apps)

        def fs_f(fts, ads, ft='f'):
            # file name contain
            if ft in fts and fts[ft]:
                v = fts[ft]
                v = v.split(' ')
                # for a, d in ads:
                #     for _f in v:
                #         for r, _, fs in os.walk(d):
                #             for f in fs:
                #                 if _f.lower() in f.lower():
                #                     print(a, ojn(r, f).replace(cls.a_ddp(a), '')[1:])
                return ((a, ojn(r, f).replace(cls.a_ddp(a), '')[1:]) for a, d in ads for _f in v for r, _, fs in
                        os.walk(d) for f in fs if _f.lower() in f.lower())
            else:
                return ((a, ojn(r, f).replace(cls.a_ddp(a), '')[1:]) for a, d in ads for r, _, fs in os.walk(d) for f in
                        fs)

        def fs_suffix(fts, afs, ft='s'):
            if ft in fts and fts[ft]:
                v = fts[ft]
                v = v.split(' ')
                return ((ap, afp) for ap, afp in afs if afp.split('.')[-1] in v)
            return afs

        def fs_not_suffix(fts, afs, ft='ns'):
            if ft in fts and fts[ft]:
                v = fts[ft]
                v = v.split(' ')
                return ((ap, afp) for ap, afp in afs if afp.split('.')[-1] not in v)
            return afs

        def fs_ctx(fts, afs, ft='ctx'):
            # todo
            if ft in fts and fts[ft]:
                v = fts[ft]
                v = v.split(' ')
            return list(afs)

        # search a=all,f=fwaas
        for search in searches.split('|'):
            keys = search.strip().split(',')
            keys = [i for i in keys if i]
            if not keys:
                continue
            for key in keys:
                if '=' not in key:
                    break
            else:
                keys = dict([k.split('=') for k in keys])
                fa = fs_a(keys)
                fd = fs_d(keys, fa)
                ff = fs_f(keys, fd)
                fs = fs_suffix(keys, ff)
                fn = fs_not_suffix(keys, fs)
                fc = fs_ctx(keys, fn)
                files.extend(fc)
        return files, len(files)

    @classmethod
    def mdr(cls, app: str, target: str) -> dict:
        print('mdr', app, target)
        t = cls.a_dfp(app, target)
        if oex(t):
            return {'status': False, 'message': 'there is exist: %s' % target}
        try:
            os.makedirs(t)
        except Exception as e:
            return {'status': False, 'message': 'failed in mkdir: %s' % e}
        return {'status': True}

    @classmethod
    def th(cls, text: str, app: str, target: str, spa=True) -> dict:
        print('th', app, target)
        if not target:
            return {'status': False, 'message': 'target is required'}
        if ':' in target:
            return {'status': False, 'message': 'target can not contain ":"'}
        t = cls.a_dfp(app, target)
        _dir = odn(t)
        if not oex(_dir):
            os.makedirs(_dir)

        try:
            if spa and oex(t) and app != APP_SQU:
                os.rename(t, '.'.join((t, cls.tsp(st=2, ed=-2), 'spa')))
            with open(t, 'w') as f:
                f.write(text)
            return {'status': True, 'target': target}
        except Exception as e:
            return {'status': False, 'message': 'touch failed: %s' % e}

    @staticmethod
    def frs(target: str, start: int, end: int, executor=None) -> list:
        # file read special
        if start == end:
            return []
        # for local: return [x for i, x in enumerate(open(target, 'r')) if start <= i + 1 <= end]
        _, stdout, stderr = executor("sed -n '%s,%sp' %s" % (start + 1, end, target))
        rsp = stdout.read().decode()
        return rsp.strip().split('\n')

    @staticmethod
    def fgc(target: str, executor=None, is_windows=False) -> int:
        # file get count'
        if is_windows:
            _, stdout, stderr = executor('find /v /c "" %s' % target)
            rsp = stdout.read().decode().strip()
            rsp = int(rsp.split(' ')[-1]) if rsp else 0
        else:
            _, stdout, stderr = executor('grep -c "" %s' % target)
            rsp = stdout.read().decode().strip()
            rsp = int(rsp) if rsp else 0

        return rsp

    @classmethod
    def get_output_file(cls, path_output: str, tid: str) -> str:
        folder = cls.tsp(ed=10)

        path_folder = ojn(path_output, folder)
        if not oex(path_folder):
            os.makedirs(path_folder)
        print(f'folder: {path_folder}, tid: {tid}')

        path_file = ojn(path_folder, tid + '.history')
        # if not oex(path_file):
        #     print('get a new file: ', path_file)
        return path_file

    @staticmethod
    def mkdir_if_not_exist(path: str) -> None:
        if oex(path) and oid(path):
            return
        print('makedirs: %s' % path)
        os.makedirs(path)

    @staticmethod
    def func_fp(path: str, func, args, kwargs) -> None:
        if args is None:
            args = ()
        if kwargs is None:
            kwargs = {}
        func(path, *args, **kwargs)

    @classmethod
    def func_file(cls, path: str, func,
                  starts=None, contains=None, ends=None,
                  args=None, kwargs=None) -> None:
        c = 0
        for r, ds, fs in os.walk(path):
            for f in fs:
                if contains and not [f for contain in contains if contain in f]:
                    continue
                if starts and not [f for start in starts if f.startswith(start)]:
                    continue
                if ends and not [f for end in ends if f.endswith(end)]:
                    continue
                c += 1
                cls.func_fp(ojn(r, f), func, args, kwargs)

    @classmethod
    def func_dir(cls, path: str, func,
                 starts=None, contains=None, ends=None,
                 args=None, kwargs=None) -> None:
        for r, ds, fs in os.walk(path):
            for f in ds:
                if contains and not [f for contain in contains if contain in f]:
                    continue
                if starts and not [f for start in starts if f.startswith(start)]:
                    continue
                if ends and not [f for end in ends if f.endswith(end)]:
                    continue
                cls.func_fp(ojn(r, f), func, args, kwargs)

    @classmethod
    def ana(cls, path, sf='.py', th=3, le=8) -> None:
        sps = ',()[]{}=+-/<>*@:&"\'\n'
        exp = ('if', 'else', 'in', 'is', 'not', 'for', 'def', 'class', '#',
               'self', 'and', 'or', 'as', 'break', 'continue', 'return',
               'True', 'None', 'False', 'list', 'dict', 'len',
               'classmethod', 'staticmethod', 'methods', 'endpoint',
               'string', 'from', 'import', 'except', 'Exception', 'ValueError',)

        def do(fp):
            if not fp.endswith(sf):
                return
            with open(fp, 'r') as f:
                v = f.read()
            for sp in sps:
                v = v.replace(sp, ' ')
            v = (i.strip() for i in v.split(' ') if i.strip())
            d = {}
            for i in v:
                if i in exp:
                    continue
                if i not in d:
                    d[i] = 0
                d[i] += 1
            v = [(k, i) for k, i in d.items() if i > th and len(k) > le]
            if not v:
                return d
            print(fp)
            v.sort(key=lambda i: i[1], reverse=True)
            for k, i in v:
                print(str(i).zfill(3), k)
            return d

        if oif(path):
            do(path)
        else:
            cls.func_file(path, do)

    @staticmethod
    def tsp(st=0, ed=None) -> str:
        # 2024-11-04 19:21:19.881024
        v = str(datetime.datetime.now())
        v = v[st:] if ed is None else v[st:ed]
        return v.replace('-', '').replace(' ', '').replace(':', '')

    @classmethod
    def check_exist_and_out_date(cls, ofp, do=(False, False)):
        do_exist, check_date = do
        if oex(ofp):
            if not do_exist:
                return True
            if not check_date:
                return True
            date = cls.tsp(ed=10)
            stmt = os.stat(ofp).st_mtime
            if date == time.strftime('%Y%m%d', time.localtime(stmt)):
                return True
        return False

    @classmethod
    def get_task_id(cls, fn_yaml) -> str:
        # 2024-11-04 19:21:19.881024
        return '.'.join((cls.tsp(st=10), fn_yaml))

    @classmethod
    def cmd_in_subprocess(cls, _cmd, _cwd, _sudo=None, _psw=None):
        if _sudo:
            _cmd = 'sudo -S ' + _cmd
        shell = subprocess.Popen(
            _cmd,
            cwd=_cwd,
            shell=True,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding='utf-8'
        )
        if _sudo:
            time.sleep(0.25)
            shell.stdin.write(_psw + '\n')
        return shell

    @classmethod
    def run_in_subprocess(cls, _func, *args, **kwargs):
        pass
        # shell = subprocess.Popen(
        #     _cmd,
        #     cwd=_cwd,
        #     shell=True,
        #     stdout=subprocess.PIPE,
        #     stderr=subprocess.PIPE,
        #     encoding='utf-8'
        # )
        # return shell

    @staticmethod
    def run_threads(_func, _params: list, _max: int = 20):
        threads = []
        for p in _params:
            t = threading.Thread(target=_func, args=p.get('args', ()), kwargs=p.get('kwargs'))
            threads.append(t)

        for t in threads:
            t.start()
            while sum([1 for _i in threads if _i.is_alive()]) > _max:
                time.sleep(0.5)

        for t in threads:
            t.join()

    @staticmethod
    def is_linux():
        return 'linux' in sys.platform.lower()

    @staticmethod
    def quarters():
        _quarters = []
        today = datetime.date.today()
        current_year = today.year
        current = str(today).replace('-', '')
        for year in range(2010, current_year + 1, 1):
            for _date in ('0331', '0630', '0930', '1231'):
                _quarter = str(year) + _date
                if _quarter < current:
                    _quarters.append(_quarter)
        return _quarters

    @classmethod
    def func_items(cls, value: dict, func, dumping=False):
        # dumping can not been removed
        if not isinstance(value, dict):
            raise TypeError('!!! __VALUE TYPE ERROR')

        # __value = {'rc': 'list(range(0,10,1))',
        #            'nc': 'list(range(0,20,1))'}
        d = {}
        for k, v in value.items():
            d[k] = func(v)
        # d = {'rc': [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
        #      'nc': [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19]}
        length = max([len(v) for k, v in d.items()])
        for k in d.keys():
            i = 0
            while len(d.get(k)) != length:
                d[k].append(d.get(k)[i])
                i += 1
        # d = {'rc': [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
        #      'nc': [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19]}
        dd = zip(*[[{k: str(i)} for i in v] for k, v in d.items()])
        ddd = []
        for i in dd:
            ii = {}
            [ii.update(iii) for iii in i]
            ddd.append(ii)
        # ddd = [{'rc': '0', 'nc': '0'},
        #        {'rc': '1', 'nc': '1'},
        #        {'rc': '2', 'nc': '2'},
        #        {'rc': '3', 'nc': '3'},
        #        {'rc': '4', 'nc': '4'},
        #        ...
        #        {'rc': '5', 'nc': '15'},
        #        {'rc': '6', 'nc': '16'},
        #        {'rc': '7', 'nc': '17'},
        #        {'rc': '8', 'nc': '18'},
        #        {'rc': '9', 'nc': '19'}]
        return ddd

    def func_replace(self, value: str, running: dict, dumping=False):
        # replace (())
        def rf(__v):
            if not isinstance(__v, str):
                return __v

            __v = __v.strip(' ')
            lc, rc = '((', '))'
            if lc not in __v or rc not in __v:
                return __v
            mix = __v
            while lc in mix and rc in mix:
                field, _ = mix.split(rc, 1)
                _, field = field.rsplit(lc, 1)

                # with param
                func, param = field.split('(') if '(' in field else (field, None)

                if func not in self.functions:
                    raise ValueError('function error: %s' % func)
                if param is None:
                    vv = self.functions.get(func)()
                    raw = lc + field + rc
                else:
                    vv = self.functions.get(func)(param)
                    raw = lc + field + rc + ')'
                mix = mix.replace(raw, vv)
            return mix

        def rv(__v):
            if not isinstance(__v, str):
                return __v

            __v = __v.strip(' ')
            lc, rc = '{{', '}}'
            if lc not in __v or rc not in __v:
                return __v
            mix, c = __v, 0

            # {{unmatched}} -> uuid
            unmatched = {}

            def get_value(key):
                if key in v:
                    return True, v.get(key)

                # a[0].b[0].c
                if '[' in key and key.endswith(']'):
                    key, index = key.split('[', 1)
                    index, _ = index.split(']', 1)
                    if key not in v or not isinstance(v.get(key), list):
                        return False, v
                    # a[0].b[0].c[0:3] or a[0].b[0].c[0]
                    if ':' in index:
                        st, ed = index.replace(' ', '').split(':')
                        return True, v.get(key)[int(st): int(ed)]
                    return True, v.get(key)[int(index)]
                return False, v

            def replace_dict(row):
                nonlocal v

                elements = row.split('.')
                count = len(elements)
                for i in range(1, count, 1):
                    left = '.'.join(elements[:i])
                    right = '.'.join(elements[i:])

                    match_left, v_left = get_value(left)
                    if match_left:
                        v = v_left
                        match_right, v_right = get_value(right)
                        if match_right:
                            v = v_right
                            return v
                        return replace_dict(right)

                if raw not in unmatched:
                    unmatched[raw] = str(uuid.uuid4())
                # unmatched = {
                #     '{{yft.rows}}': '2954a66b-c9b9-4d4f-8579-7b69682bff39'
                # }
                return unmatched.get(raw)

            while lc in mix and rc in mix:
                # todo: {"a":{"b":["c","d"]}} -H {{HEADER-LOGIN}}
                field, _ = mix.split(rc, 1)
                _, field = field.rsplit(lc, 1)
                raw = lc + field + rc
                if field in running:
                    vv = running.get(field)
                    # todo
                    if raw == mix:
                        return vv
                    if isinstance(vv, tuple):
                        vv = list(vv)
                    mix = mix.replace(raw, json.dumps(vv) if dumping else str(vv))
                    continue
                v = copy.deepcopy(running)
                v = replace_dict(field)
                if isinstance(v, (dict, list, tuple, int, float)):
                    # todo
                    if raw == mix:
                        return v
                    raise ValueError('value type error: %s' % v)
                mix = mix.replace(raw, v)

            # uui -> {{unmatched}}
            while [tmp for raw, tmp in unmatched.items() if tmp in mix]:
                for raw, tmp in unmatched.items():
                    if tmp not in mix:
                        continue
                    mix = mix.replace(tmp, raw)
            return mix

        d = rv(rf(rv(rf(value))))
        return d

    @classmethod
    def func_transform(cls, value: str, _: dict, dumping=False):
        # dumping can not been remove
        # transform --
        if not value.startswith('--'):
            return value
        values = {}
        # --name vpn.01.ext1 --shared True --router:external True
        items = value.split('--')
        items = [i.strip() for i in items if i.strip()]
        # items = [
        #     'X86 cirros-x86',
        #     'DISK 1', 'RAM 128',
        #     'X86-FILE ((PATH_OPEN_SOURCES))/images/cirros-0.6.1-x86_64-disk.img',
        #     'A64 cirros-a64-uvv',
        #     'DISK 1',
        #     'RAM 128',
        #     'A64-FILE ((PATH_OPEN_SOURCES))/images/cirros-0.6.1-aarch64-disk.img'
        # ]
        for i in items:
            kv = i.split(' ', 1)
            if len(kv) != 2:
                key, v = kv[0], ''
            else:
                key, v = kv
            # print('key: "%s", value: "%s"' % (key, value))
            if v.lower() in ('false',):
                v = False
            elif v.lower() in ('null',):
                v = None
            elif v.lower() in ('true',):
                v = True
            values[key] = v
        # values = {
        #     'X86': 'cirros-x86',
        #     'DISK': '1',
        #     'RAM': '128',
        #     'X86-FILE': '((PATH_OPEN_SOURCES))/images/cirros-0.6.1-x86_64-disk.img',
        #     'A64': 'cirros-a64-uvv',
        #     'A64-FILE': '((PATH_OPEN_SOURCES))/images/cirros-0.6.1-aarch64-disk.img'}
        return values

    @classmethod
    def display_params(cls, params, running, func, key_except=None, dumping=False):
        if isinstance(params, str):
            return func(params, running, dumping=dumping)
        if isinstance(params, (list, tuple, dict)):
            items = params.items() if isinstance(params, dict) else enumerate(params)
            for i, v in list(items):
                if isinstance(params, dict):
                    # key except
                    if key_except and i in key_except:
                        continue
                    # key replace
                    ii = func(i, running, dumping=dumping)
                    if ii != i:
                        params.pop(i)
                        i = ii
                if isinstance(v, str):
                    params[i] = func(v, running, dumping=dumping)
                elif isinstance(v, (dict, list, tuple)):
                    params[i] = cls.display_params(v, running, func, key_except, dumping)
        return params

    @staticmethod
    def sf_yyyy():
        return str(datetime.datetime.now().year).zfill(4)

    @staticmethod
    def sf_mm():
        return str(datetime.datetime.now().month).zfill(2)

    @staticmethod
    def sf_dd():
        return str(datetime.datetime.now().day).zfill(2)

    @staticmethod
    def sf_hh():
        return str(datetime.datetime.now().hour).zfill(2)

    @classmethod
    def sf_yyyymm(cls):
        return cls.sf_yyyy() + cls.sf_mm()

    @classmethod
    def sf_yyyymmdd(cls):
        return cls.sf_yyyy() + cls.sf_mm() + cls.sf_dd()

    @classmethod
    def sf_mmdd(cls):
        return cls.sf_mm() + cls.sf_dd()

    @classmethod
    def sf_mmddhh(cls):
        return cls.sf_mm() + cls.sf_dd() + cls.sf_hh()

    @classmethod
    def sf_ddhh(cls):
        return cls.sf_dd() + cls.sf_hh()

    @classmethod
    def sf_ddhhmm(cls):
        now = datetime.datetime.now()
        return cls.sf_dd() + cls.sf_hh() + str(now.minute).zfill(2)

    @classmethod
    def sf_ddhhmmss(cls):
        now = datetime.datetime.now()
        return cls.sf_dd() + cls.sf_hh() + str(now.minute).zfill(2) + str(now.second).zfill(2)

    @staticmethod
    def sf_ip_weekly():
        return '192.168.98.7%s' % (datetime.datetime.now().weekday() + 1)

    @staticmethod
    def sf_ip_monthly():
        return '192.168.98.%s' % str(datetime.datetime.now().month)

    @staticmethod
    def sf_ts_version(version):
        text = requests.get('http://192.168.3.7/develop/').text
        prefix = 'tristack-install--%s' % version
        suffix = '.tar.gz'
        tmp = text.split(prefix)[-1]
        tmp = tmp[:tmp.find(suffix)]
        return prefix + tmp

    @staticmethod
    def sf_path_project():
        fp = os.path.dirname(os.path.abspath(__file__))
        if os.path.exists(fp):
            return fp
        raise FileNotFoundError('project not found: %s' % fp)

    @classmethod
    def sf_path_open_sources(cls):
        fp = os.path.join(os.path.dirname(cls.sf_path_project()), 'OPEN-SOURCES')
        if os.path.exists(fp):
            return fp
        raise FileNotFoundError('project OPEN-SOURCES not found: %s' % fp)

    def sf_current_history(self):
        return self.ins.current_his

    @property
    def functions(self):
        return {
            'MMDDHH': self.sf_mmddhh,
            'MMDD': self.sf_mmdd,
            'MM': self.sf_mm,
            'DD': self.sf_dd,
            'DDHH': self.sf_ddhh,
            'DDHHmm': self.sf_ddhhmm,
            'DDHHmmss': self.sf_ddhhmmss,
            'YYYY': self.sf_yyyy,
            'YYYYMM': self.sf_yyyymm,
            'YYYYMMDD': self.sf_yyyymmdd,
            'IP_WEEKLY': self.sf_ip_weekly,
            'IP_MONTHLY': self.sf_ip_monthly,
            'GET_TS_VERSION': self.sf_ts_version,
            'PATH_PROJECT': self.sf_path_project,
            'PATH_OPEN_SOURCES': self.sf_path_open_sources,
            'CURRENT_HISTORY': self.sf_current_history,
        }


class MetaController(object):
    E_EXECUTE = 'EXECUTE'
    E_RESUME = 'RESUME'
    E_PAUSE = 'PAUSE'
    E_STOP = 'STOP'

    def __init__(self, ns=None, afp=None):
        self.ns = ns
        self.afp = afp
        self.mc_status = self.E_STOP
        self.mc_event = None
        self.init()
        self.start()

    def init(self):
        if self.afp is None:
            raise ValueError('AFP IS NONE')
        ins.ins_tasks[self.afp] = self

    def uninit(self):
        task = ins.ins_tasks.pop(self.afp, None)
        if task:
            task.stop()

    def is_executing(self):
        return self.mc_status in (self.E_EXECUTE, self.E_RESUME,)

    def is_paused(self):
        return self.mc_status in (self.E_PAUSE,)

    def is_stopped(self):
        return self.mc_status in (self.E_STOP,)

    def start(self):
        self.action(event=self.E_EXECUTE)

    def resume(self):
        self.action(event=self.E_RESUME)

    def pause(self):
        self.action(event=self.E_PAUSE)

    def stop(self):
        self.action(event=self.E_STOP)

    def action(self, event=None):
        if event:
            self.mc_event = event

        if not self.mc_event:
            return

        def ep():
            self.mc_status = self.E_PAUSE
            while self.mc_event == self.mc_status == self.E_PAUSE:
                if isinstance(self.ns, MetaWebSocket):
                    self.ns.progress(self, self.afp)
                time.sleep(0.5)

        def rp():
            ep()

        def pr():
            self.mc_status = self.E_RESUME

        def s():
            self.mc_status = self.E_STOP
            if isinstance(self.ns, MetaWebSocket):
                self.ns.progress(self, self.afp)
            self.uninit()
            raise EOFError('STOP BY EVENT')

        def e():
            self.mc_status = self.E_EXECUTE

        status_event_map = {
            # valid
            ':'.join((self.E_EXECUTE, self.E_PAUSE,)): ep,
            ':'.join((self.E_EXECUTE, self.E_STOP,)): s,
            ':'.join((self.E_RESUME, self.E_PAUSE,)): rp,
            ':'.join((self.E_RESUME, self.E_STOP,)): s,
            ':'.join((self.E_PAUSE, self.E_RESUME,)): pr,
            ':'.join((self.E_PAUSE, self.E_STOP,)): s,
            ':'.join((self.E_STOP, self.E_EXECUTE,)): e,
        }
        status_event = ':'.join((self.mc_status, self.mc_event))
        # invalid
        if status_event not in status_event_map:
            self.mc_event = None
            if isinstance(self.ns, MetaWebSocket):
                self.ns.progress(self, self.afp)
            return
        # valid
        status_event_map[status_event]()
        if isinstance(self.ns, MetaWebSocket):
            self.ns.progress(self, self.afp)
        self.mc_event = None


class MetaWebSocket(Namespace, MetaFile):

    def __init__(self, *args, **kwargs):
        MetaFile.__init__(self)
        Namespace.__init__(self, *args, **kwargs)
        self.apis = {}
        self.events = {}

    def is_execute(self, afp):
        pass

    def on_connect(self):
        return True

    def on_disconnect(self):
        pass

    def on_join(self, data):
        self.print('join: %s' % data)
        afp = data.get('room')
        join_room(afp)
        inst = ins.ins_tasks.get(afp)
        if inst and not inst.is_stopped():
            self.progress(inst, afp)

    def progress(self, inst, room):
        if inst and self.socketio:
            self.emit('progress', data={'status': inst.mc_status, 'at': room}, room=room)

    def api_stop(self, data):
        afp = data.get('at')
        task = ins.ins_tasks.get(afp)

        if task and (task.is_paused() or task.is_executing()):
            self.print('STOP AFP(%s, %s)' % (id(task), afp), room=afp)
            try:
                task.uninit()
            except EOFError:
                pass
            return
        self.print('WARNING: AFP(%s) IS NOT RUNNING' % afp, room=afp)

    def api_resume(self, data):
        afp = data.get('at')
        inst = ins.ins_tasks.get(afp)

        if inst and inst.is_paused():
            self.print('RESUME AFP(%s, %s)' % (id(inst), afp), room=afp)
            inst.resume()
            return
        self.print('WARNING: AFP(%s) IS NOT RUNNING' % afp, room=afp)

    def api_pause(self, data):
        afp = data.get('at')
        inst = ins.ins_tasks.get(afp)

        if inst and inst.is_executing():
            self.print('PAUSE AFP(%s, %s)' % (id(inst), afp), room=afp)
            inst.pause()
            return
        self.print('WARNING: AFP(%s) IS NOT RUNNING' % afp, room=afp)

    def api_execute(self, data):
        afp = data.get('at')
        task = ins.ins_tasks.get(afp)

        # executing
        if task and task.is_executing():
            self.print('WARNING: AFP(%s, %s) IS RUNNING' % (id(task), afp), room=afp)
            return
        # paused
        elif task and task.is_paused():
            self.print('WARNING: AFP(%s, %s) IS PAUSED' % (id(task), afp), room=afp)
            return
        # stopped
        elif task:
            try:
                task.uninit()
            except EOFError:
                pass

        # self.afp is required for self.print
        self.afp = afp
        self.print('EXECUTE: %s, %s' % (afp, datetime.datetime.now()))
        ts1 = time.perf_counter()
        ts2 = time.time()

        try:
            action = data.get('action')
            event = action.split(':')[-1].upper()
            self.events[event](data)
        except EOFError as _:
            pass
        except Exception as e:
            self.print('ERROR: %s' % repr(e), room=afp)
            self.print('TRACE: %s' % traceback.format_exc(), room=afp)

        self.print('STOP: %s, %s' % (afp, datetime.datetime.now()), room=afp)
        self.print('TOTAL COST: %s, %s' % (round(time.perf_counter() - ts1, 5),
                                           round(time.time() - ts2, 5)), room=afp)
        task = ins.ins_tasks.get(afp)
        if task:
            try:
                task.uninit()
            except EOFError:
                pass

    def on_task(self, data):
        api = self.apis.get(data.get('action'))
        self.socketio.start_background_task(api, data)


# class MetaSocketIO(MetaFile):
#
#     def __init__(self, *args, **kwargs):
#         MetaFile.__init__(self)
#         Namespace.__init__(self, *args, **kwargs)
#         self.apis = {}
#         self.events = {}
#
#     def is_execute(self, afp):
#         pass
#
#     def on_connect(self):
#         return True
#
#     def on_disconnect(self):
#         pass
#
#     def on_join(self, data):
#         self.print('join: %s' % data)
#         afp = data.get('at')
#         join_room(afp)
#         inst = ins.ins_tasks.get(afp)
#         if inst and not inst.is_stopped():
#             self.progress(inst, afp)
#
#     def progress(self, task, room):
#         if task:
#             self.emit('progress', data={'status': task.mc_status, 'at': room}, room=room)
#             # self.print('AFP(id %s) %s %s -> %s' % (id(inst), inst.afp, inst.mc_status, inst.mc_event))
#
#     def api_stop(self, data):
#         afp = data.get('at')
#         task = ins.ins_tasks.get(afp)
#
#         if task and (task.is_paused() or task.is_executing()):
#             self.print('STOP AFP(%s, %s)' % (id(task), afp))
#             try:
#                 task.uninit()
#             except EOFError:
#                 pass
#             return
#         self.print('WARNING: AFP(%s) IS NOT RUNNING' % afp)
#
#     def api_resume(self, data):
#         afp = data.get('at')
#         inst = ins.ins_tasks.get(afp)
#
#         if inst and inst.is_paused():
#             self.print('RESUME AFP(%s, %s)' % (id(inst), afp))
#             inst.resume()
#             return
#         self.print('WARNING: AFP(%s) IS NOT RUNNING' % afp)
#
#     def api_pause(self, data):
#         afp = data.get('at')
#         inst = ins.ins_tasks.get(afp)
#
#         if inst and inst.is_executing():
#             self.print('PAUSE AFP(%s, %s)' % (id(inst), afp))
#             inst.pause()
#             return
#         self.print('WARNING: AFP(%s) IS NOT RUNNING' % afp)
#
#     def api_execute(self, data):
#         afp = data.get('at')
#         task = ins.ins_tasks.get(afp)
#
#         # executing
#         if task and task.is_executing():
#             self.print('WARNING: AFP(%s, %s) IS RUNNING' % (id(task), afp))
#             return
#         # paused
#         elif task and task.is_paused():
#             self.print('WARNING: AFP(%s, %s) IS PAUSED' % (id(task), afp))
#             return
#         # stopped
#         elif task:
#             try:
#                 task.uninit()
#             except EOFError:
#                 pass
#
#         # self.afp is required for self.print
#         self.afp = afp
#         self.print('EXECUTE: %s, %s' % (afp, datetime.datetime.now()))
#         ts1 = time.perf_counter()
#         ts2 = time.time()
#
#         try:
#             action = data.get('action')
#             event = action.split(':')[-1].upper()
#             self.events[event](data)
#         except EOFError as _:
#             pass
#         except Exception as e:
#             self.print('ERROR: %s' % repr(e))
#             self.print('TRACE: %s' % traceback.format_exc())
#
#         self.print('STOP: %s, %s' % (afp, datetime.datetime.now()))
#         self.print('TOTAL COST: %s, %s' % (round(time.perf_counter() - ts1, 5),
#                                            round(time.time() - ts2, 5)))
#
#         task = ins.ins_tasks.get(afp)
#         if task:
#             try:
#                 task.uninit()
#             except EOFError:
#                 pass
#
#     def on_task(self, data):
#         api = self.apis.get(data.get('action'))
#         self.socketio.start_background_task(api, data)
