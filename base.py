# -*- coding: utf-8 -*-
import os
import sys
import json
import copy
import time
import uuid
import base64
import shutil
import logging
import datetime
import importlib
import threading
import traceback
import subprocess
import multiprocessing
from multiprocessing.dummy import Process

import requests
import yaml
import paramiko
from flask import make_response
from flask_socketio import Namespace
from flask_socketio import join_room

import ins
import cons
import independence

opjn = os.path.join
opid = os.path.isdir
opif = os.path.isfile
opdn = os.path.dirname
opsp = os.path.split
opex = os.path.exists
opap = os.path.abspath

PATH_PROJECT = opdn(opap(__file__))
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


def make_response_with_headers(data):
    r = make_response(data)
    r.headers['Server'] = 'TPA'
    r.headers['Connection'] = 'Keep-Alive'
    r.headers['Access-Control-Allow-Credentials'] = 'true'
    return r


class MetaProcess(multiprocessing.Process):

    def __init__(self, func, *args, **kwargs):
        super(MetaProcess, self).__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs

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


class MetaStack(object):
    # F_NODES = 'NODES'
    # F_ROLES = 'ROLES'
    # F_LOCAL = ('LOCAL', 'LOCALHOST', '', '127.0.0.1')

    def __init__(self, setting):
        self.roles = {}
        # self.sshes = {}
        # self.sftps = {}
        self.tokens = {}
        # self.__apis__ = {}
        # self.headers = {}
        # self.api_attrs = {}
        self.__parser(setting)

    def __api(self, device, service, uri):
        return self.services.get(service).get(cons.O_STACK_URI) % device + uri

    def __parser(self, setting):
        self.apis = setting.get(cons.O_STACK_APIS, {})
        self.headers = setting.get(cons.O_HEADERS, {})
        self.hosts = {}
        for n, host in setting.get(cons.O_HOSTS, {}).items():
            v = copy.deepcopy(setting.get(cons.O_HOST_DEFAULT, {}))
            v.update(host)
            self.hosts[n] = v
        if not self.hosts:
            raise ValueError('!!! HOSTS IN SETTING IS EMPTY ')
        self.logs = setting.get(cons.O_HOST_LOGS, [])
        self.meta = {}
        for service, apis in self.apis.items():
            for api, attr in apis.items():
                if cons.O_GID not in attr:
                    continue
                self.meta[attr.get(cons.O_GID)] = (service, api)
        self.services = setting.get(cons.O_STACK_SERVICES, {})

    def validate_nodes(self, nodes):
        for node in nodes:
            if node in cons.V_LOCAL:
                continue
            if node not in self.hosts:
                raise ValueError('invalidate node: %s' % node)

    def wait_online(self, node, timeout, ins_dsp):
        if node not in self.hosts:
            raise KeyError('wait_online error, node not exist: %s' % node)

        # self.sshes.pop(node, None)
        # self.sftps.pop(node, None)

        nd = self.hosts.get(node)
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        remain = int(timeout)
        unit = 5
        online = False
        time.sleep(unit)
        while remain > 0:
            rel_start = time.time()
            try:
                ssh.connect(nd['device'], username=nd['ssh_user'], password=nd['ssh_psw'], timeout=unit)
                online = True
                break
            except Exception as e:
                cost = time.time() - rel_start
                remain = int(remain - unit - cost)
                if remain > 0:
                    ins_dsp.print('%s in wait_online, wait in: %s' % (repr(e), remain))
            ins_dsp.action()
            time.sleep(unit)

        if online:
            ins_dsp.print('online: %s' % node)
        else:
            ins_dsp.print('online failed: %s' % node)

    def get_sudo_psw(self, node):
        if node not in self.hosts:
            raise KeyError('get_ssh error, node not exist: %s' % node)
        return self.hosts.get(node).get('ssh_psw')

    def get_ssh(self, node):
        if node not in self.hosts:
            raise KeyError('get_ssh error, node not exist: %s' % node)
        # if node in self.sshes:
        #     return self.sshes[node]
        nd = self.hosts.get(node)
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        for ic in range(3):
            try:
                ssh.connect(nd['device'], username=nd['ssh_user'], password=nd['ssh_psw'], timeout=8)
                break
            except TimeoutError as e:
                if ic == 2:
                    raise e
            except Exception as e:
                raise e
        # self.sshes[node] = ssh
        return ssh

    def get_sftp(self, node):
        if node not in self.hosts:
            raise KeyError('get_ssh error, node not exist: %s' % node)
        # if node in self.sftps:
        #     return self.sftps[node]
        nd = self.hosts.get(node)
        ftp = paramiko.Transport(nd['device'])
        for ic in range(3):
            try:
                ftp.connect(username=nd['ssh_user'], password=nd['ssh_psw'])
                break
            except TimeoutError as e:
                if ic == 2:
                    raise e
            except Exception as e:
                raise e
        sftp = paramiko.SFTPClient.from_transport(ftp)
        # self.sftps[node] = sftp
        return ftp, sftp

    def ud(self, node, src, dst):
        # upload
        pass

    def dd(self, node, src, dst):
        # download
        pass

    def g_token(self, node, service='identity'):
        if node not in self.hosts:
            raise KeyError('!!! NODE: %s NOT FOUND IN HOSTS: %s' % (node, self.hosts))
        if service in self.tokens and node in self.tokens[service]:
            return self.tokens.get(service).get(node)
        host = self.hosts.get(node)
        rsp = requests.post(
            self.__api(host.get('device'), service, '/auth/tokens'),
            headers={'Content-Type': 'application/json'},
            data=json.dumps({
                "auth": {
                    "identity": {
                        "methods": [
                            "password"
                        ],
                        "password": {
                            "user": {
                                "name": host.get('name'),
                                "domain": {
                                    "name": host.get('domain')
                                },
                                "password": host.get('password')
                            }
                        }
                    }
                }
            }),
            verify=False
        )
        if rsp.status_code not in (200, 201):
            raise ValueError(rsp.text)
        result = rsp.headers['x-subject-token']
        if service not in self.tokens:
            self.tokens[service] = {}
        self.tokens[service][node] = result
        print('token', result)
        return result

    def g_session(self, node, service):
        if node not in self.hosts:
            raise KeyError('!!! NODE: %s NOT FOUND IN HOSTS: %s' % (node, self.hosts))
        # if service in self.tokens and node in self.tokens[service]:
        #     return self.tokens[service][node]
        host = self.hosts.get(node)
        t = requests.Session()
        try:
            r = t.post(
                self.__api(host.get('device'), service, '/auth/'),
                headers={'Accept': 'application/json, text/plain, */*',
                         'Content-Type': 'application/json;charset=UTF-8'},
                json={"username": host.get('name'),
                      "password": host.get('password')},
                verify=False)
            if r.status_code != 200:
                print(r.status_code)
                print(r.text)
            else:
                # print(r.json())
                pass
        except Exception as e:
            print(str(e))
            raise e
        return t

    def api(self, node, service, operate, resource):
        if node not in self.hosts:
            raise KeyError('!!! NODE: %s NOT FOUND IN HOSTS: %s' % (node, self.hosts))
        if service not in self.services:
            raise KeyError('!!! SERVICE: %s NOT FOUND' % service)
        auth = self.services.get(service).get(cons.O_STACK_AUTH_TYPE)
        is_session = auth == cons.O_STACK_AUTH_SESSION
        device = self.hosts.get(node).get('device')
        methods = {
            'list': 'get',
            'create': 'post',
            'show': 'get',
            'patch': 'patch',
            'update': 'put',
            'delete': 'delete',
        }

        def __request(op, sv, ur, data, header, file):
            method = methods[op]
            url = self.__api(device, sv, ur)
            data = {} if data is None else data
            if auth == cons.O_STACK_AUTH_SESSION:
                # request with session for tn
                url = url if url.endswith('/') else url + '/'
                data = independence.wraps_data_in_get(data) if method in ('get',) else data
                session = self.g_session(node, sv)
            elif auth == cons.O_STACK_AUTH_TOKEN:
                # request with token for openstack
                url = url[:-1] if url.endswith('/') else url
                if 'X-Auth-Token' not in header:
                    header.update({'X-Auth-Token': self.g_token(node)})
                session = requests
            elif auth == cons.O_STACK_AUTH_NONE:
                session = requests
            else:
                session = requests

            params = {'params': data} if method in ('get', 'delete') else {'data': json.dumps(data)}

            for ic in range(3):
                try:
                    if file:
                        with open(file, 'rb') as f:
                            rsp = session.request(method, url, headers=header, data=f, verify=False)
                    else:
                        rsp = session.request(method, url, headers=header, timeout=360, **params)
                    break
                except requests.exceptions.ConnectTimeout as e:
                    if ic == 2:
                        if is_session:
                            session.close()
                        raise e
                except Exception as e:
                    if is_session:
                        session.close()
                    raise e
            if is_session:
                session.close()
            return rsp

        def __api(op, s, r):
            # @wrj
            def ___api(data, header, file=None):
                _id = data.pop('id', None) if data else None
                _pid = data.pop('pid', None) if data else None
                _uid = data.pop('uid', None) if data else None

                if _pid and _uid:
                    rr = r.format(pid=_pid, uid=_uid)
                elif _pid:
                    rr = r.format(pid=_pid)
                elif _uid:
                    rr = r.format(uid=_uid)
                else:
                    rr = r

                return __request(op, s, rr + _id if _id else rr, data, header, file)

            return ___api

        if service not in self.apis:
            raise KeyError('!!! SERVICE NOT FOUND: %s' % service)
        if resource not in self.apis.get(service):
            raise KeyError('!!! RESOURCE: %s NOT FOUND IN SERVICE: %s' % (resource, service))
        uri = self.apis.get(service).get(resource).get(cons.O_STACK_URI)
        if not uri:
            raise KeyError('!!! RUI NOT FOUND IN SERVICE: %s, RESOURCE: %s' % (service, resource))
        return __api(operate, service, uri)


class MetaFile(object):
    E_EXECUTE = 'EXECUTE'
    E_PAUSE = 'PAUSE'
    E_STOP = 'STOP'

    # E_ALL = (E_EXECUTE, E_PAUSE, E_STOP)

    def __init__(self):
        self.debug = False
        self.afp = None
        self.ns = None
        self.task_id = None
        self.current_his = None
        self.event = None
        self.status = self.E_STOP

    def pause(self):
        self.event = self.E_PAUSE

    def stop(self):
        self.event = self.E_STOP

    def action(self):
        if not self.event:
            return

        self.status = self.event
        if isinstance(self.ns, Namespace):
            self.ns.progress({'status': self.status, 'at': self.afp}, self.afp)

        if self.event == self.E_EXECUTE:
            return
        elif self.event == self.E_STOP:
            ins.ins_tasks.pop(self.afp, None)
            raise EOFError('STOP BY EVENT')
        while self.event == self.E_PAUSE:
            time.sleep(1.2345)
            if isinstance(self.ns, Namespace):
                self.ns.progress({'status': self.status, 'at': self.afp}, self.afp)

    @staticmethod
    def ly(t):
        if not opex(t):
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

    def print(self, pt, wt=None, nolog=False):
        if isinstance(pt, (dict, list, tuple)):
            try:
                pt = json.dumps(pt, indent=2)
            except Exception as err:
                pt = json.dumps({'error': str(err), 'pt': str(pt)}, indent=2)
        else:
            pt = str(pt)
        if isinstance(self, Namespace) and self.afp:
            self.emit('his', data=pt + '\n', room=self.afp)
        if isinstance(self.ns, Namespace) and self.afp:
            self.ns.emit('his', data=pt + '\n', room=self.afp)
        print(pt)
        current_his = None if 'current_his' not in self.__dict__ else self.current_his
        if not current_his:
            print('WARNING: THERE IS NOT CURRENT_HIS')
            return

        if nolog:
            wt = 'NOLOG IS True'
        else:
            if wt is not None:
                if isinstance(wt, (dict, list, tuple)):
                    try:
                        wt = json.dumps(wt, indent=2)
                    except Exception as err:
                        wt = json.dumps({'error': str(err), 'wt': str(wt)}, indent=2)
                else:
                    wt = str(wt)
            else:
                wt = pt
        with open(current_his, 'a') as file:
            file.write(wt + '\n')

    @staticmethod
    def __request_parser_args(args_r):
        if not args_r:
            return None, None, None, None, None
        search = args_r['search'] if 'search' in args_r and args_r['search'] else None
        sort = args_r['sort'] if 'sort' in args_r and args_r['sort'] else None
        order = args_r['order'] if 'order' in args_r and args_r['order'] else None
        offset = int(args_r['offset']) if 'offset' in args_r and args_r['offset'] else None
        limit = int(args_r['limit']) if 'limit' in args_r and args_r['limit'] else None
        return search, sort, order, offset, limit

    @classmethod
    def __view_img(cls, t):
        with open(t, 'rb') as f:
            b64 = 'data:;base64,' + str(base64.b64encode(f.read()))[2:-1]
            return {'status': True, 'rows': b64, 'is_image': True, 'type': 'img'}

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
            if not i:
                continue
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
        ap = cls.a_ddp(app)
        fp = opjn(ap, dfp)
        if not opap(fp).startswith(ap):
            raise ValueError('unknown target: %s' % dfp)
        # fp = '/home/zin/Desktop/_Y/TPA/timing/data/ENCRYPT.tim'
        return fp

    @classmethod
    def a_dfp(cls, app, target):
        # app data file path
        # app = 'star'
        # target = 'STARS.sta'
        ap = cls.a_ddp(app)
        fp = opjn(ap, target)
        if not opap(fp).startswith(ap):
            raise ValueError('unknown target: %s' % target)
        # fp = '/home/zin/Desktop/_Y/TPA/star/data/STARS.sta'
        return fp

    @classmethod
    def aep(cls, app, edp, target):
        fp = cls.a_afp(':'.join((app, edp)) if edp else app + ',' + target)
        return fp

    @staticmethod
    def a_ddp(a: str):
        # a: app
        # app data dir path
        # a = 'timing'
        a, e = a.split(':') if ':' in a else (a, None)
        if a not in cons.Apps.apps:
            raise ValueError('unknown app: %s' % a)
        if a in (cons.APP_ENC, cons.APP_ZOO):
            return opdn(PATH_PROJECT)
        dp = opjn(opjn(PATH_PROJECT, a), 'data')
        dp = dp if not e else opjn(dp, e)
        # dp = '/home/zin/Desktop/_Y/TPA/timing/data'
        return dp

    @classmethod
    @independence.timer
    def dd(cls, app: str, target: str):
        print('dd', app, target)

        v = cls.a_dfp(app, target)
        _, fn = opsp(v)
        lw = target.lower()
        # txt
        fnd = '%s.%s.txt' % (fn, cls.tsp(ed=17))
        # img xls
        for end in ('.jpg', '.png', '.jpeg', '.webp', '.xlsx', '.xls'):
            if lw.endswith(end):
                fnd = fn
                break
        with open(v, 'rb') as f:
            ctx = f.read()
        response = make_response(ctx)
        response.headers['Content-Type'] = 'application/octet-stream'

        # for CN
        from urllib.parse import quote

        response.headers['Content-Disposition'] = "attachment; filename*=utf-8''%s" % (quote(fnd))
        return response

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
                ctime = stat.st_ctime
                mtime = stat.st_mtime
                size = os.path.getsize(_fp) / 1024.0
                size = str(round(size / 1024.0, 1)) + 'M' if size > 2048 else str(round(size, 1)) + 'K'
                _, fn = opsp(_fp)
                r.append({
                    'fn': fn,
                    'isdir': opid(_fp),
                    'ctime': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(ctime)),
                    'mtime': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(mtime)),
                    'size': size,
                    'app': _app,
                    'afp': afp,
                    'id': afp,
                    'tpa': [ii for ii in range(10)],
                })
            return r

        if search is not None:
            # search
            files, total = cls.fs(app, target, search)
        else:
            fp = cls.a_dfp(app, target)
            files, total = [], 0
            if opex(fp) and opid(fp):
                files = [f for f in os.listdir(fp) if not f.startswith('.')]
                if suffix:
                    # to fix
                    files = [f for f in files if f.endswith(suffix) or opid(cls.a_dfp(app, opjn(target, f)))]
                files.sort(reverse=True)
                total = len(files)
                files = ((app, opjn(target, f)) for f in files)

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
        if not opex(v):
            return {'status': False, 'message': 'there is not exist: %s' % target, 'type': 'txt'}
        if not opif(v):
            return {'status': False, 'message': 'is not a file: %s' % target, 'type': 'txt'}

        fd, fn = opsp(target)
        lw = fn.lower()
        target = '/'.join((app, target))
        target_split = target.split('/')
        parents = [{'i': e, 'i_path': '/'.join(target_split[1:i + 1])} for i, e in enumerate(target_split)]
        pfn = {'parents': parents, 'fn': fn, 'app': app, 'parent': fd}
        # img
        for end in ('.jpg', '.png', '.jpeg', '.webp'):
            if lw.endswith(end):
                rsp = cls.__view_img(v)
                rsp.update(pfn)
                return rsp
        # xls
        for end in ('.xlsx', '.xls'):
            if lw.endswith(end):
                rsp = cls.__view_xls(v, args_r)
                rsp.update(pfn)
                return rsp
        # txt
        try:
            rsp = cls.__view_txt(v)
            rsp.update(pfn)
            return rsp
        except Exception as e:
            return {'status': False, 'message': 'unknown file: %s' % e, 'type': 'txt'}

    @classmethod
    @independence.timer
    def de(cls, app: str, files: str) -> dict:
        print('de', files, app)
        failed = []
        message = 'delete success'
        for fn in files.split(','):
            fp = cls.a_dfp(app, fn)
            try:
                if opid(fp):
                    shutil.rmtree(fp)
                else:
                    os.remove(fp)
            except Exception as e:
                failed.append(fp)
                message = 'failed in delete: %s' % e
        return {'status': False if failed else True, 'message': message}

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
            if opid(fp):
                continue
            try:
                if fp.endswith('sh'):
                    cls.__execute_sh(fp)
                elif fp.endswith('py'):
                    cls.__execute_py(fp)
            except Exception as e:
                failed.append(fn)
                print(traceback.format_exc())
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
                    v = [a for a in cons.Apps.apps if a not in (cons.APP_ZOO, cons.APP_ENC)]
                else:
                    v = v.split(' ')
                # filter 
                if ins.ins_bps:
                    v = [i for i in v if i in ins.ins_bps]
                apps = []
                [apps.extend(cons.Apps.edps(i)) for i in v]
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
                #                     print(a, opjn(r, d))
                return ((a, opjn(r, d)) for a in apps for _d in v for r, ds, _ in os.walk(cls.a_ddp(a)) for d in ds if _d.lower() in d.lower())
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
                #                     print(a, opjn(r, f).replace(cls.a_ddp(a), '')[1:])
                return ((a, opjn(r, f).replace(cls.a_ddp(a), '')[1:]) for a, d in ads for _f in v for r, _, fs in os.walk(d) for f in fs if _f.lower() in f.lower())
            else:
                return ((a, opjn(r, f).replace(cls.a_ddp(a), '')[1:]) for a, d in ads for r, _, fs in os.walk(d) for f in fs)

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
                pass
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
        if opex(t):
            return {'status': False, 'message': 'there is exist: %s' % target}
        try:
            os.makedirs(t)
        except Exception as e:
            return {'status': False, 'message': 'failed in mkdir: %s' % e}
        return {'status': True}

    @classmethod
    def th(cls, text: str, app: str, target: str) -> dict:
        print('th', app, target)
        if not target:
            return {'status': False, 'message': 'target is required'}
        if ':' in target:
            return {'status': False, 'message': 'target can not contain ":"'}
        t = cls.a_dfp(app, target)
        _dir = opdn(t)
        if not opex(_dir):
            os.makedirs(_dir)

        try:
            if opex(t):
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
            # self.print('  WITHOUT LOG: %s' % target)
            return []
        # for local: return [x for i, x in enumerate(open(target, 'r')) if start <= i + 1 <= end]
        _, stdout, stderr = executor("sed -n '%s,%sp' %s" % (start + 1, end, target))
        rsp = stdout.read().decode()
        # self.print('  LOG: %s\n  %s' % (target, rsp))
        return rsp.strip().split('\n')

    @staticmethod
    def fgc(target: str, executor=None) -> int:
        # file get count
        _, stdout, stderr = executor('grep -c "" %s' % target)
        rsp = stdout.read().decode().strip()
        rsp = int(rsp) if rsp else 0
        # self.print('file_get_count: %s' % rsp)
        return rsp

    @classmethod
    def get_output_file(cls, path_output: str, tid: str) -> str:
        folder = cls.tsp(ed=10)

        path_folder = opjn(path_output, folder)
        if not opex(path_folder):
            os.makedirs(path_folder)
        print('path_folder: %s, tid: %s' % (path_folder, tid))

        path_file = opjn(path_folder, tid + '.history')
        if not opex(path_file):
            print('get a new file: ', path_file)
        return path_file

    @staticmethod
    def mkdir_if_not_exist(path: str) -> None:
        if opex(path) and opid(path):
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
        for r, ds, fs in os.walk(path):
            for f in fs:
                if contains and not [f for contain in contains if contain in f]:
                    continue
                if starts and not [f for start in starts if f.startswith(start)]:
                    continue
                if ends and not [f for end in ends if f.endswith(end)]:
                    continue
                cls.func_fp(opjn(r, f), func, args, kwargs)

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
                cls.func_fp(opjn(r, f), func, args, kwargs)

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

        if opif(path):
            do(path)
        else:
            cls.func_file(path, do)

    @staticmethod
    def tsp(st=0, ed=None) -> str:
        v = str(datetime.datetime.now())
        v = v[st:] if ed is None else v[st:ed]
        return v.replace('-', '').replace(' ', '').replace(':', '')

    @classmethod
    def get_task_id(cls, fn_yaml) -> str:
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
            # print('_pm:', p)
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

                if func not in self.STRING_FUNCTIONS:
                    raise ValueError('function error: %s' % func)
                if param is None:
                    vv = self.STRING_FUNCTIONS[func]()
                    raw = lc + field + rc
                else:
                    vv = self.STRING_FUNCTIONS[func](param)
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
                # print('!!! UNMATCHED: %s' % raw)
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
                if isinstance(v, (dict, list, tuple)):
                    # todo
                    if raw == mix:
                        return v
                    raise ValueError('value type error: %s' % v)
                mix = mix.replace(raw, v)
                pass

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
            else:
                pass
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
                else:
                    pass
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
        return cls.sf_dd() + cls.sf_hh() + str(now.minute).zfill(2) + str(now.minute).zfill(2)

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
    def STRING_FUNCTIONS(self):
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
            'IP_WEEKLY': self.sf_ip_weekly,
            'IP_MONTHLY': self.sf_ip_monthly,
            'GET_TS_VERSION': self.sf_ts_version,
            'PATH_PROJECT': self.sf_path_project,
            'PATH_OPEN_SOURCES': self.sf_path_open_sources,
            'CURRENT_HISTORY': self.sf_current_history,
        }


class MetaWebSocket(Namespace, MetaFile):

    def __init__(self, *args, **kwargs):
        MetaFile.__init__(self)
        Namespace.__init__(self, *args, **kwargs)
        self.actions = {}

    def is_execute(self, afp):
        pass

    def on_connect(self):
        return True

    def on_disconnect(self):
        pass

    def on_join(self, data):
        self.print('join: %s' % data)
        join_room(data.get('at'))

    def progress(self, data, room):
        self.emit('progress', data=data, room=room)

    def on_task(self, data):
        action = data.get('action')
        event = action.split(':')[-1].upper()

        self.afp = data.get('at')
        if self.afp in ins.ins_tasks:
            status = ins.ins_tasks.get(self.afp).status
            if event == self.E_EXECUTE and status in (self.E_EXECUTE,):
                self.print('WARNING: %s IS RUNNING' % self.afp)
                return
            if event in (self.E_STOP, self.E_PAUSE) and status in (self.E_STOP,):
                self.print('WARNING: %s IS NOT RUNNING' % self.afp)
                return

        def do(d):
            ts1 = time.perf_counter()
            ts2 = time.time()

            if event == self.E_EXECUTE:
                self.print('START: %s\n' % datetime.datetime.now())
            try:
                self.actions[d.get('action')](d)
            except EOFError as _:
                pass
            except Exception as e:
                self.print('ERROR: %s' % repr(e))
                self.print('TRACE: %s' % traceback.format_exc())
            if event == self.E_EXECUTE:
                self.print('')
                self.print('END: %s' % datetime.datetime.now())
                self.print('COST: %s, %s ' % (round(time.perf_counter() - ts1, 5),
                                              round(time.time() - ts2, 5)))
            self.progress({'status': self.E_STOP, 'at': self.afp}, self.afp)

        self.socketio.start_background_task(do, data)


if __name__ == '__main__':
    pass
