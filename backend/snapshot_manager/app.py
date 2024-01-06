import logging

from contextvars import ContextVar
from pathlib import Path
from typing import Callable

from fastapi import APIRouter, FastAPI, Request, WebSocket
from fastapi.responses import FileResponse
from prometheus_client import Gauge
from starlette_exporter import PrometheusMiddleware, handle_metrics

from snapshot_manager.generic.debug import DEBUG_GLOBAL
from snapshot_manager.kube_controller import KubeController
from snapshot_manager.ws_controller import WSController

from .config import Config
from .context_vars import CONTROLLER, KUBE_CONTROLLER1, KUBE_CONTROLLER2
from .controller import AWSController


config = Config()
UP = Gauge('up', 'Snapshot Manager is up', ['app'])
UP.labels(app='snapshot_manager').set(1)

CONTROLLER.set(AWSController())
debug_global = DEBUG_GLOBAL.get()
KUBE_CONTROLLER1.set(KubeController(config.KUBECONFIG1, 'kube1', debug=debug_global))
KUBE_CONTROLLER2.set(KubeController(config.KUBECONFIG2, 'kube2', debug=debug_global))

STATIC = Path('./frontend/kube-snapshot-manager/build')
INDEX = STATIC / 'index.html'

Path('.log').mkdir(exist_ok=True)

log = logging.getLogger('app')

for name in ['aioboto3', 'aiobotocore', 'kubernetes_asyncio']:
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


CANCELLATIONS = ContextVar[None | list[Callable]]('cancellations', default=None)
HAS_DEBUG_LOOP = ContextVar[bool]('has_debug_loop', default=False)


@root.websocket('/api/ws')
async def ws(sock: WebSocket):
    try:
        sock_controller = WSController(sock, debug=debug_global)
        await sock_controller.start()
        await sock_controller.finished.wait()
    except Exception as e:
        log.exception(f'WS error: {e}')


async def setup_controllers():
    c = CONTROLLER.get()
    await c.startup()
    log.debug(f'{CONTROLLER=}')
    kc1 = KUBE_CONTROLLER1.get()
    await kc1.start()
    c.add_cluster(kc1)

    kc2 = KUBE_CONTROLLER2.get()
    await kc2.start()
    c.add_cluster(kc2)


async def shutdown_controllers():
    c = CONTROLLER.get()
    await c.shutdown()
    kc1 = KUBE_CONTROLLER1.get()
    await kc1.stop()
    kc2 = KUBE_CONTROLLER2.get()
    await kc2.stop()


async def errors_loggin_middleware(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception as e:
        log.exception(e)
        raise


def get_app() -> FastAPI:
    app = FastAPI(on_startup=[setup_controllers], on_shutdown=[shutdown_controllers])
    app.include_router(root)
    app.add_middleware(
        PrometheusMiddleware,
        app_name='snapshot_manager',
        skip_paths=['/metrics'],
        filter_unhandled_paths=True,
    )
    app.middleware('http')(errors_loggin_middleware)
    return app
