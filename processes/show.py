from sanic import Sanic
from sc_app import app
from sanic.log import server_logger


def show(foo):
    server_logger.info(str(foo))


@app.main_process_ready
async def ready(x: Sanic, _):
    x.manager.manage("show", show, {"foo": x})
