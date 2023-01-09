import asyncio
import logging
from contextvars import ContextVar
from pathlib import Path

from fastapi import APIRouter, FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.websockets import WebSocketState
from prometheus_client import Gauge
from pydantic import BaseModel
from starlette_exporter import handle_metrics, PrometheusMiddleware

from fan_tools.fan_logging import setup_logger

from .controller import Controller
from .models import SnaphotsEvent, VolumesEvent


UP = Gauge('up', 'Snapshot Manager is up', ['app'])
UP.labels(app='snapshot_manager').set(1)
CONTROLLER = ContextVar('controller', default=Controller())
STATIC = Path('./frontend/kube-snapshot-manager/build')
INDEX = STATIC / 'index.html'

Path('.log').mkdir(exist_ok=True)
setup_logger('snapshot_manager', '.log')
log = logging.getLogger('app')

for name in ['aioboto3', 'aiobotocore']:
    logging.getLogger(name).setLevel(logging.INFO)


root = APIRouter()
root.add_route('/metrics', handle_metrics)


@root.get('/')
async def index():
    return FileResponse(INDEX)


@root.get('/static/{file_path:path}')
async def get_static(file_path: str):
    path = STATIC / file_path
    path2 = STATIC / (file_path + '.html')
    if path.is_file() and path.is_relative_to(STATIC):
        return FileResponse(path)
    elif path2.is_file() and path2.is_relative_to(STATIC):
        return FileResponse(path2)
    return FileResponse(INDEX)


@root.websocket('/api/ws')
async def ws(sock: WebSocket):
    c = CONTROLLER.get()
    out_queue = asyncio.Queue()
    unsubscribe = c.subscribe(out_queue)

    await sock.accept()
    await sock.send_json({'event': 'echo'})

    async def out_loop():
        while True:
            event: BaseModel = await out_queue.get()
            if event is None:
                return
            if sock.client_state == WebSocketState.DISCONNECTED:
                return
            await sock.send_text(event.json())

    loop = asyncio.create_task(out_loop())

    try:
        await c.describe_volumes()
        while True:
            msg = await sock.receive_json()
            if msg['event'] == 'get_snapshots':
                await c.describe_snapshots()
            else:
                log.info(f'Unknown message: {msg}')
    except WebSocketDisconnect:
        log.debug('disconnected')
    finally:
        unsubscribe()
        loop.cancel()


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
    return app
