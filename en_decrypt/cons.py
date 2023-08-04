import os

from cons import PATH_PROJECT
from cons import PATH_HISTORY as HIS
from cons import APP_ENC as APP

BASE = os.path.join(PATH_PROJECT, APP)
DATA = os.path.join(BASE, 'data')

EDP_ENC = APP

FDS = dict([(edp, {'scripts': os.path.join(DATA, os.path.join(edp, 'scripts')),
                   'his': os.path.join(HIS, os.path.join('data', '%s' % edp)),
                   'pks': os.path.join(DATA, os.path.join(edp, 'pks')),
                   'data': os.path.dirname(PATH_PROJECT), }) for edp in (EDP_ENC,)])
