# -*- coding: utf-8 -*-
# !/bin/python3

import os
import time
import ctypes

# from Crypto.Cipher import AES

from base import MetaFile


class EncryptHelper(MetaFile):
    # 已加密文件头部特征
    header_encrypt = 'encrypted:'
    bin_header_encrypt = bytes(header_encrypt.encode('utf-8'))
    len_header_encrypt = len(bin_header_encrypt)

    def __init__(self, psw_aes=None, psw_stream=None, at=None):
        super(EncryptHelper, self).__init__()
        self.afp = at
        # AES密钥
        self.psw_aes = psw_aes
        self.bin_psw_aes = bytearray(psw_aes.encode('utf-8'))
        # 流密钥
        self.psw_stream = psw_stream
        self.bin_psw_stream = bytearray(psw_stream.encode('utf-8'))
        # 加密/解密
        self.do_encrypt = True
        # 单个文件大小最大值
        self.max_size = 64
        # 仅处理
        self.include = []
        # 不处理
        self.exclude = []

    @staticmethod
    def _get_file_size(_file):
        # 获取文件大小
        _size = os.path.getsize(_file) / 1024 / 1024.00
        # print(_file, _size)
        return _size

    def _encrypt_by_str(self, __path_in):
        # 流加密, 对称
        # print('encrypt_by_str')
        with open(__path_in, 'rb') as f:
            raw = f.read()

        length_key = len(self.psw_stream)
        encrypt = bytearray()
        encrypt += self.bin_header_encrypt
        k = 0
        for _i in raw:
            _j = self.bin_psw_stream[k % length_key]
            encrypt.append(_i ^ _j)
            k += 1
        try:
            with open(__path_in, 'wb') as f:
                f.write(encrypt)
        except Exception as e:
            print('\rpass', __path_in, e)

    def _encrypt_by_aes(self, __path_in):
        # AES加密, 对称
        # print('encrypt_by_aes')
        with open(__path_in, 'rb') as f:
            cipher = AES.new(self.bin_psw_aes, AES.MODE_EAX)
            cipher_text, tag = cipher.encrypt_and_digest(f.read())
        try:
            with open(__path_in, 'wb') as f:
                [f.write(x) for x in (cipher.nonce, tag, cipher_text)]
        except Exception as e:
            print('\rpass:', __path_in, e)

    def _decrypt_by_aes(self, __path_in):
        # AES解密, 对称
        # print('decrypt_by_aes')
        with open(__path_in, 'rb') as f:
            nonce, tag, cipher_text = [f.read(x) for x in (16, 16, -1)]
            cipher = AES.new(self.bin_psw_aes, AES.MODE_EAX, nonce)
        try:
            text = cipher.decrypt_and_verify(cipher_text, tag)

            with open(__path_in, 'wb') as f:
                f.write(text)
        except Exception as e:
            print('\rpass', __path_in, e)

    def _decrypt_by_str(self, __path_in):
        # 流解密, 对称
        # print('decrypt_by_str')
        with open(__path_in, 'rb') as f:
            _raw = f.read()
            raw = _raw[self.len_header_encrypt:]

        length_key = len(self.psw_stream)
        decrypt = bytearray()
        k = 0
        for _i in raw:
            _j = self.bin_psw_stream[k % length_key]
            decrypt.append(_i ^ _j)
            k += 1
        try:
            with open(__path_in, 'wb') as f:
                f.write(decrypt)
        except Exception as e:
            print('\rpass', __path_in, e)

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

    def _is_pass(self, _file):
        # x.py.i.serial
        # 分片文件
        if _file.endswith('.serial'):
            # 计算文件名
            _file = '.'.join(_file.split('.')[:-2])

        # 仅处理
        if self.include:
            # 不在仅处理列表内
            if _file not in self.include:
                # 跳过该文件
                return True
        # 不处理
        elif self.exclude:
            # 在不处理列表内
            if _file in self.include:
                # 跳过该文件
                return True
        # 其他情况不跳过该文件
        return False

    def _encrypt_or_decrypt(self, _path_in):

        if not os.path.exists(_path_in):
            return

        ts = time.time()

        def _do(_path_file):

            with open(_path_file, 'rb') as f:
                text = f.read()
                # 忽略空文件
                if not text.strip():
                    print('ignore:', _path_file, end='')
                    return

            with open(_path_file, 'rb') as f:
                line = f.readline()

            # 文件已加密
            if line.startswith(self.bin_header_encrypt):
                # 正在进行加密
                if self.do_encrypt:
                    # 忽略
                    return
                # 正在进行解密
                # 流解密
                self._decrypt_by_str(_path_file)
                # AES解密
                self._decrypt_by_aes(_path_file)
                return
            # 文件未加密
            # 正在进行加密
            if self.do_encrypt:
                # AES加密
                self._encrypt_by_aes(_path_file)
                # 流加密
                self._encrypt_by_str(_path_file)
                return
            # 正在进行解密
            pass

        if os.path.isfile(_path_in):
            _do(_path_in)
            print('\nend encrypt_file, cost:', time.time() - ts, ' file index:', 1)
            return

        if os.path.isdir(_path_in):
            # 计算总数
            total = sum([len(files) for root, dirs, files in os.walk(_path_in)])
            index = 0
            for root, dirs, files in os.walk(_path_in):
                for file in files:
                    index += 1
                    # 检查是否跳过该文件
                    if self._is_pass(file):
                        continue

                    _file = os.path.join(root, file)
                    _do(_file)
                    print('\rprocess:', index, '/', total, end='')
            print('\nend encrypt_file, cost:', time.time() - ts, ' file index:', index)

    @classmethod
    def is_encrypted(cls, _path_in):
        with open(_path_in, 'rb') as f:
            line = f.readline()

        return True if line.startswith(cls.bin_header_encrypt) else False

    def security(self, _path_in):
        # 文件加解密
        print('do_encrypt:', self.do_encrypt)
        print('path_in:', _path_in)

        # 加密前分片
        if self.do_encrypt:
            self._separate(_path_in, 45)

        # 加密/解密
        self._encrypt_or_decrypt(_path_in)
        # 解密后组装
        if not self.do_encrypt:
            self._combine(_path_in)

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
        # parser
        # self.ns = ns

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
