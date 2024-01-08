import os

PATH_PROJECT = os.path.dirname(os.path.abspath(__file__))
PATH_HISTORY = os.path.join(PATH_PROJECT, 'history')
PATH_ZOO = PATH_PROJECT

APP_ALL = 'all'
APP_ZOO = 'zoo'
APP_SEC = 'security'
APP_FIN = 'finansis'
APP_KNO = 'know'
APP_DSP = 'dsp'
APP_HIS = 'history'
APP_ENC = 'en_decrypt'
APP_SQU = 'squirrel'
APP_TIM = 'timing'
APP_USR = 'user'
APP_STA = 'star'
APP_SPA = 'spatiotemporal'

EDP_DF = 'df'
EDP_PY = 'py'
EDP_IM = 'image'


class Apps(object):
    apps = {
        APP_SEC: (APP_SEC + ':tsunami', APP_SEC + ':suricata'),
        # APP_ZOO: (APP_ZOO + ':images', ),
        APP_FIN: (APP_FIN + ':py', APP_FIN + ':df'),
        APP_KNO: (APP_KNO + ':site', APP_KNO + ':dom'),
        APP_DSP: (APP_DSP + ':yfd', APP_DSP + ':yft'),
        APP_HIS: (APP_HIS, ),
        APP_ENC: (APP_ENC, ),
        APP_SQU: (APP_SQU, ),
        APP_TIM: (APP_TIM, ),
        # APP_USR: (APP_USR, ),
        APP_STA: (APP_STA, ),
        APP_SPA: (APP_SPA, ),
    }
