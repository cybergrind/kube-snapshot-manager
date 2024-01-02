import asyncio
import json
import logging
from contextvars import ContextVar
from pathlib import Path
from typing import Callable

from fastapi import APIRouter, FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.websockets import WebSocketState
from prometheus_client import Gauge
from pydantic import BaseModel
from snapshot_manager.kube_controller import KubeController
from starlette_exporter import handle_metrics, PrometheusMiddleware
from snapshot_manager.generic.debug import DEBUG_GLOBAL

from .config import Config
from .context_vars import CONTROLLER, KUBE_CONTROLLER1, KUBE_CONTROLLER2
from .controller import AWSController
from .models import SnaphotsEvent, VolumesEvent


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


def get_kube_controller(event, default_cluster=None) -> KubeController:
    cluster = event.get('cluster', default_cluster)
    if cluster == 'kube1':
        return KUBE_CONTROLLER1.get()
    elif cluster == 'kube2':
        return KUBE_CONTROLLER2.get()
    else:
        raise ValueError(f'Unknown cluster {event=}')


CANCELLATIONS = ContextVar[None | list[Callable]]('cancellations', default=None)
HAS_DEBUG_LOOP = ContextVar[bool]('has_debug_loop', default=False)


@root.websocket('/api/ws')
async def ws(sock: WebSocket):
    try:
        await ws_accept(sock)
    except Exception as e:
        log.exception(f'WS error: {e}')
    finally:
        cancellations = CANCELLATIONS.get()
        if cancellations:
            for cancellation in cancellations:
                try:
                    log.debug(f'WS cancelling {cancellation}')
                    cancellation()
                except Exception as e:
                    log.exception(f'WS cancellation error: {e}')
        CANCELLATIONS.set(None)


async def refresh_debug(sock: WebSocket):
    try:
        while True:
            await send_debug(sock)
            await asyncio.sleep(5)
    except (WebSocketDisconnect, asyncio.CancelledError) as e:
        log.debug(f'WS debug cancelled: {e}')


async def send_debug(sock: WebSocket, sections={}):
    if not sections:
        kc1 = KUBE_CONTROLLER1.get()
        if not kc1:
            await sock.send_text(json.dumps({'error': 'kube1 not configured'}))
            return
        kc2 = KUBE_CONTROLLER2.get()
        if not kc2:
            await sock.send_text(json.dumps({'error': 'kube2 not configured'}))
            return
        debug_object = DEBUG_GLOBAL.get()
        log.debug(f'{debug_object=}')
        sections = debug_object.serialize()
    log.debug(f'{sections=}')
    data = {
        'event': 'debug_info',
        'sections': sections,
    }
    log.debug(f'debug {data=} {sock=}')
    try:
        await sock.send_text(json.dumps(data))
    except Exception as e:
        log.exception(f'WS debug error: {e}')
        raise


async def ws_accept(sock: WebSocket):
    log.info('WS')
    c = CONTROLLER.get()
    if not c:
        log.warning('AWS not configured')
        await sock.close()
        return

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
            elif msg['event'] == 'get_debug':
                if HAS_DEBUG_LOOP.get():
                    continue
                HAS_DEBUG_LOOP.set(True)
                task = asyncio.create_task(refresh_debug(sock))
                debug_global = DEBUG_GLOBAL.get()

                def _send_debug(data):
                    asyncio.create_task(send_debug(sock, data))

                def _cancel_notify():
                    debug_global.remove_notify(_send_debug)

                debug_global.add_notify(_send_debug)
                cancellations = CANCELLATIONS.get() or []

                CANCELLATIONS.set(cancellations + [task.cancel, _cancel_notify])
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
    app.add_middleware(
        PrometheusMiddleware,
        app_name='snapshot_manager',
        skip_paths=['/metrics'],
        filter_unhandled_paths=True,
    )
    app.middleware('http')(errors_loggin_middleware)
    return app
