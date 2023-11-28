import asyncio
import json
import logging
from contextvars import ContextVar
from pathlib import Path

from fastapi import APIRouter, FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.websockets import WebSocketState
from prometheus_client import Gauge
from pydantic import BaseModel
from snapshot_manager.kube_controller import KubeController
from starlette_exporter import handle_metrics, PrometheusMiddleware

from .config import Config
from .context_vars import CONTROLLER, KUBE_CONTROLLER1, KUBE_CONTROLLER2
from .controller import AWSController
from .models import SnaphotsEvent, VolumesEvent


config = Config()
UP = Gauge('up', 'Snapshot Manager is up', ['app'])
UP.labels(app='snapshot_manager').set(1)

CONTROLLER.set(AWSController())
KUBE_CONTROLLER1.set(KubeController(config.KUBECONFIG1, 'kube1'))
KUBE_CONTROLLER2.set(KubeController(config.KUBECONFIG2, 'kube2'))

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


def get_kube_controller(event, default_cluster=None) -> KubeController:
    cluster = event.get('cluster', default_cluster)
    if cluster == 'kube1':
        return KUBE_CONTROLLER1.get()
    elif cluster == 'kube2':
        return KUBE_CONTROLLER2.get()
    else:
        raise ValueError(f'Unknown cluster {event=}')


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
                await c.describe_snapshots(reset=msg.get('force'))
            elif msg['event'] == 'snapshot_fill_tags':
                description = msg['description']
                volume_id = description.split()[-1]
                assert volume_id.startswith('vol-')

                kc = get_kube_controller(msg)
                pv_by_volume = await kc.pv_by_volume()
                pv = pv_by_volume.get(volume_id)
                if not pv:
                    log.warning(f'No PV for {volume_id=}')
                    continue
                claim_ref = pv.spec.claim_ref
                tags = {'namespace': claim_ref.namespace, 'name': claim_ref.name}
                await c.set_tags(msg['snap_id'], tags)
                await c.describe_snapshots(reset=True)

            elif msg['event'] == 'get_pvs':
                cluster = msg.get('cluster', 'kube1')
                kc = get_kube_controller(msg)
                pvs = await kc.get_pvs()
                await sock.send_text(
                    json.dumps(
                        {'event': 'pvs', 'pvs': [pv.dict() for pv in pvs], 'cluster': cluster}
                    )
                )
            elif msg['event'] == 'create_snapshot':
                kc = get_kube_controller(msg)
                log.debug(f'got {kc=}')
                await kc.create_pv_snapshot(msg['pvid'], f'snapshot-{msg["pvid"]}')
            elif msg['event'] == 'delete_snapshot':
                kc = get_kube_controller(msg, 'kube1')
                # await kc.get_snapshot_by_snapid(msg['snap_id'])
                await kc.delete_snapshot_by_snapid(msg['snap_id'])
            elif msg['event'] == 'snapshot_toggle_deletion_policy':
                kc = get_kube_controller(msg, 'kube1')
                await kc.snapshot_toggle_deletion_policy(msg['snap_id'])
                c.aws_describe_snapshots.reset_cache()
                await c.describe_snapshots()
            else:
                log.info(f'Unknown message: {msg}')
    except WebSocketDisconnect:
        log.debug('disconnected')
    finally:
        unsubscribe()
        loop.cancel()


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
    app.add_middleware(PrometheusMiddleware, app_name='snapshot_manager', skip_paths=['/metrics'])
    app.middleware('http')(errors_loggin_middleware)
    return app
