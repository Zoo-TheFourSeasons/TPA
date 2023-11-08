# -*- coding: utf-8 -*-
"""app
"""

from sanic import Sanic
from sc_logger import logs

app = Sanic(__name__, log_config=logs)
app.static('/static', 'bs5/static')
app.update_config('./sc_configs.py')
app.configure_logging = True

