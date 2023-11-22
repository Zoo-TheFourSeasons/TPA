# -*- coding: utf-8 -*-
# !/bin/python3

import os
import ctypes

from base import MetaFile


class EncryptHelper(MetaFile):

    def __init__(self):
        super(MetaFile, self).__init__()

    @staticmethod
    def _get_file_size(_file):
        # 获取文件大小
        _size = os.path.getsize(_file) / 1024 / 1024.00
        # print(_file, _size)
        return _size

    @classmethod
    def _combine(cls, _path_in):
        _tmp = {}
        for root, dirs, files in os.walk(_path_in):
            for _file in files:
                # 不是文件片
                if not _file.endswith('.serial'):
                    continue
                # # 检查是否跳过该文件
                # if cls._is_pass(_file):
                #     continue
                print('\r_combine:', _file, end='')
                _path = os.path.join(root, _file)
                _file_raw = '.'.join(_file.split('.')[:-2])
                _path_raw = os.path.join(root, _file_raw)
                if _path_raw not in _tmp:
                    _tmp[_path_raw] = []
                _tmp[_path_raw].append(_path)

        for _path_raw, _file_serial in _tmp.items():
            with open(_path_raw, 'ab') as _f:
                for _file_i in _file_serial:
                    with open(_file_i, 'rb') as __f:
                        _f.write(__f.read())
                    # 移除文件片
                    os.remove(_file_i)

    @classmethod
    def _separate(cls, _path_in, _max_size):
        # 大文件分片
        for root, dirs, files in os.walk(_path_in):
            for _file in files:
                # 检查是否跳过该文件
                # if self._is_pass(_file):
                #     print('\r_is_pass:', _file, end='')
                #     continue
                # 未达到分片阈值
                _path = os.path.join(root, _file)
                _size = cls._get_file_size(_path)
                if _size < _max_size:
                    # print('<max_size', _file)
                    continue
                print('\r_separate:', _file, end='')
                # 分片
                _i = 1
                _zfill = len(str(int((_size + _max_size - 1) / _max_size)))
                with open(_path, 'rb') as _f:
                    i_file = _f.read(_max_size * 1024 * 1024)
                    while i_file:
                        # 文件片i
                        _file_i = _path + '.' + str(_i).zfill(_zfill) + '.serial'
                        with open(_file_i, 'wb') as __ff:
                            __ff.write(i_file)
                        # 文件片i+1
                        _i += 1
                        i_file = _f.read(_max_size * 1024 * 1024)
                # 分片后移除自身
                os.remove(_path)

    @classmethod
    def separate(cls, app, target, do_separate, max_size):
        # 文件加解密
        print('path_in:', target)

        # separate
        target_abs = cls.a_dfp(app, target)
        do_separate = True if do_separate == 'SEPARATE' else False
        if do_separate:
            cls._separate(target_abs, int(max_size))
        # combine
        else:
            cls._combine(target_abs)

    @classmethod
    def security_by_golang(
            cls, app, target, do_encrypt, psw_aes, nonce, psw_stream,
            max_size: int = 45):

        for path_in in target.split(','):
            target_abs = cls.a_dfp(app, path_in)
            # validate
            if not os.path.exists(target_abs):
                raise FileNotFoundError('there is not exist: %s' % target_abs)

        if len(psw_aes) != 32 or len(psw_stream) != 32 or len(nonce) != 24:
            raise ValueError('len(psw_aes | psw_stream) != 32 | len(nonce) != 24')

        do_encrypt = True if do_encrypt == 'ENCRYPT' else False
        # do
        try:
            lib = ctypes.cdll.LoadLibrary('./en_decrypt/encrypt.go.so')
            for path_in in target.split(','):
                target_abs = cls.a_dfp(app, path_in)
                lib.security(do_encrypt,
                             psw_aes.encode('utf-8'),
                             psw_stream.encode('utf-8'),
                             nonce.encode('utf-8'),
                             target_abs.encode('utf-8'),
                             max_size)
                print('success in security, target: %s' % target_abs)
            return {'status': True}
        except Exception as e:
            print('failed in security_by_golang, e: %s' % repr(e))
            return {'status': False, 'message': repr(e)}

    @classmethod
    def timing(cls, app, target, do_encrypt, fp_token, max_size: int = 45):
        token = cls.ly(fp_token)
        psw_aes = token.get('AES')
        psw_stream = token.get('STREAM')
        nonce = token.get('NONCE')
        cls.security_by_golang(app, target, do_encrypt, psw_aes, nonce, psw_stream, max_size)
