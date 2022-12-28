import asyncio
import logging
from contextvars import ContextVar
from pathlib import Path

from fastapi import APIRouter, FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
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

Path('.log').mkdir(exist_ok=True)
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
    await sock.send_json({'event': 'echo'})
    c = CONTROLLER.get()

    # if closed = return

    out_queue = asyncio.Queue()
    unsubscribe = c.subscribe(out_queue)

    async def out_loop():
        while True:
            event: BaseModel = await out_queue.get()
            if event is None:
                return
            if sock.client_state == WebSocketState.DISCONNECTED:
                return
            await sock.send_text(event.json())

    loop = asyncio.create_task(out_loop())

    volumes = await c.describe_volumes()
    await sock.send_text(VolumesEvent(volumes=volumes).json())

    while True:
        try:
            msg = await sock.receive_json()
            if msg['event'] == 'get_snapshots':
                snapshots = await c.describe_snapshots()
                if sock.client_state == WebSocketState.DISCONNECTED:
                    return
                await sock.send_text(SnaphotsEvent(snapshots=snapshots).json())
            else:
                log.info(f'Unknown message: {msg}')
        except WebSocketDisconnect:
            break
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
    app.mount(
        '/static',
        StaticFiles(directory=Path('./frontend/kube-snapshot-manager/build')),
        name='static',
    )
    return app
