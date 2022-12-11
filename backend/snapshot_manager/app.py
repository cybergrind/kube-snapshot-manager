import logging
from contextvars import ContextVar
from pathlib import Path

from fastapi import APIRouter, FastAPI, WebSocket
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from prometheus_client import Gauge
from starlette_exporter import handle_metrics, PrometheusMiddleware

from fan_tools.fan_logging import setup_logger

from .controller import Controller


UP = Gauge('up', 'Snapshot Manager is up', ['app'])
UP.labels(app='snapshot_manager').set(1)
CONTROLLER = ContextVar('controller', default=Controller())

setup_logger('snapshot_manager', '.log')
log = logging.getLogger('app')

for name in ['aioboto3', 'aiobotocore']:
    logging.getLogger(name).setLevel(logging.INFO)


root = APIRouter()
root.add_route('/metrics', handle_metrics)


@root.get('/')
async def index():
    return FileResponse(Path('./frontend/kube-snapshot-manager/build/index.html'))


@root.websocket('/api/ws')
async def ws(sock: WebSocket):
    log.debug('Got connection')
    await sock.accept()
    await sock.send_json({'type': 'echo'})
    c = CONTROLLER.get()
    volumes = await c.describe_volumes()
    await sock.send_json({'type': 'volumes', 'volumes': volumes})
    msg = await sock.receive_json()


async def setup_controller():
    c = CONTROLLER.get()
    await c.startup()
    log.debug(f'{CONTROLLER=}')


async def shutdown_controller():
    c = CONTROLLER.get()
    await c.shutdown()


def get_app() -> FastAPI:
    app = FastAPI(on_startup=[setup_controller], on_shutdown=[shutdown_controller])
    app.include_router(root)
    app.add_middleware(PrometheusMiddleware, app_name='snapshot_manager', skip_paths=['/metrics'])
    app.mount(
        '/static',
        StaticFiles(directory=Path('./frontend/kube-snapshot-manager/build')),
        name='static',
    )
    return app
