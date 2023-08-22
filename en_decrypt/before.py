import os

from base import MetaFile
import cons


def init_folders():
    fds = [{'his': os.path.join(MetaFile.a_ddp(cons.APP_HIS), MetaFile.a_edp(adp)),
            'data': MetaFile.a_ddp(adp)} for adp in cons.Apps.apps.get(cons.APP_ENC)]
    for fd in fds:
        for _, path in fd.items():
            if not os.path.exists(path):
                os.makedirs(path)
                print('make dirs: %s' % path)


inits = [init_folders, ]
