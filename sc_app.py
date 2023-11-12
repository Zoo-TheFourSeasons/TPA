# -*- coding: utf-8 -*-
"""app
"""

from sanic import Sanic
from socketio import AsyncServer

from sc_logger import logs

app = Sanic(__name__, log_config=logs)
app.static('/static', 'bs5/static')
app.update_config('./sc_configs.py')
app.configure_logging = True

sio = AsyncServer(async_mode='sanic')
sio.attach(app)


# @app.listener('before_server_start')
# def before_server_start(sanic, loop):
#     sio.start_background_task(background_task)
