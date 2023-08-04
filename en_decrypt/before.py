import os

from en_decrypt.cons import FDS


def init_folders():
    for app, fds in FDS.items():
        for fd, path in fds.items():
            if not os.path.exists(path):
                os.makedirs(path)
                print('makedirs: %s' % path)


inits = [init_folders, ]
