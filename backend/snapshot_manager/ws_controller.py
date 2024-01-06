import asyncio
import json
import logging
import typing

from fastapi import WebSocket, WebSocketDisconnect
from fastapi.websockets import WebSocketState
from pydantic import BaseModel

from snapshot_manager.context_vars import CONTROLLER, KUBE_CONTROLLER1, KUBE_CONTROLLER2
from snapshot_manager.generic.controller import Controller, State
from snapshot_manager.generic.debug import DEBUG_GLOBAL


if typing.TYPE_CHECKING:
    from snapshot_manager.kube_controller import KubeController


log = logging.getLogger(__name__)


def get_kube_controller(event, default_cluster=None) -> 'KubeController':
    cluster = event.get('cluster', default_cluster)
    if cluster in ['kube1', 'kube2']:
        kc = KUBE_CONTROLLER1.get() if cluster == 'kube1' else KUBE_CONTROLLER2.get()
        if kc:
            return kc
    raise ValueError(f'Unknown cluster {event=}')


async def refresh_debug(sock: WebSocket, controller: Controller):
    try:
        while True:
            await send_debug(sock)
            await asyncio.sleep(5)
    except RuntimeError:
        log.debug('WS refresh_debug got RuntimeError')
        controller.set_state(State.STOPPING)
        controller.timer.trigger()
    except (WebSocketDisconnect, asyncio.CancelledError) as e:
        log.debug(f'WS debug cancelled: {e}')
        controller.set_state(State.STOPPING)
        controller.timer.trigger()


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
        sections = debug_object.serialize()
    log.debug(f'{sections=}')
    data = {
        'event': 'debug_info',
        'sections': sections,
    }
    log.debug(f'debug {data=} {sock=}')
    try:
        await sock.send_text(json.dumps(data))
    except RuntimeError:
        raise
    except Exception as e:
        log.exception(f'WS debug error: {e}')
        raise


async def safe_send_debug(sock: WebSocket, controller: Controller):
    try:
        await send_debug(sock)
    except RuntimeError:
        log.info('WS safe_send_debug got RuntimeError')


class WSController(Controller):
    def __init__(self, sock: WebSocket, *args, **kwargs):
        self.sock = sock
        self.finished = asyncio.Event()
        self.debug_loop: asyncio.Task | None = None
        self.out_loop = asyncio.create_task(self.run_out_loop())
        self.out_queue = asyncio.Queue()
        self.in_loop: asyncio.Task | None = None
        self.on_stop = []
        super().__init__(*args, **kwargs)

    async def run_out_loop(self):
        while self.is_running:
            event: BaseModel = await self.out_queue.get()
            if event is None:
                self.set_state(State.STOPPING)
                return
            if self.sock.client_state == WebSocketState.DISCONNECTED:
                self.set_state(State.STOPPING)
                return
            try:
                await self.sock.send_text(event.json())
            except Exception as e:
                log.exception(f'WS error: {e}')
                self.set_state(State.STOPPING)
                return

    async def startup(self):
        log.info('WS')
        c = CONTROLLER.get()
        sock = self.sock
        if not c:
            log.warning('AWS not configured')
            await sock.close()
            self.set_state(State.STOPPING)
            return

        self.unsubscribe = c.subscribe(self.out_queue)
        await sock.accept()
        await sock.send_json({'event': 'echo'})
        await c.describe_volumes()
        self.in_loop = asyncio.create_task(self.run_in_loop())

    async def run_in_loop(self):
        c = CONTROLLER.get()
        if not c:
            return
        sock = self.sock
        try:
            while self.is_running:
                msg = await sock.receive_json()
                log.debug(f'WS got {msg=}')
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
                    if self.debug_loop:
                        continue
                    self.debug_loop = asyncio.create_task(refresh_debug(sock, self))
                    debug_global = DEBUG_GLOBAL.get()

                    def _send_debug(data):
                        asyncio.create_task(safe_send_debug(sock, data))

                    def _cancel_notify():
                        debug_global.remove_notify(_send_debug)
                        debug_global.remove_child(self.debug)

                    debug_global.add_notify(_send_debug)
                    self.on_stop.append(_cancel_notify)
                else:
                    log.info(f'Unknown message: {msg}')
        except (WebSocketDisconnect, RuntimeError):
            self.set_state(State.STOPPING)
        except Exception as e:
            self.set_state(State.STOPPING)
            log.exception(f'WS error: {e}')
            raise

    async def on_error(self, exception):
        log.exception(f'WS error: {exception}')
        if self.sock.client_state == WebSocketState.DISCONNECTED:
            self.set_state(State.STOPPING)
            return True

    async def loop_iteration(self):
        if self.sock.client_state == WebSocketState.DISCONNECTED:
            self.set_state(State.STOPPING)
        if self.debug:
            self.debug.track('sock.client_state', str(self.sock.client_state))

    async def shutdown(self):
        for task in [self.debug_loop, self.out_loop, self.in_loop]:
            if task and not task.done():
                task.cancel()

        for callback in self.on_stop:
            try:
                callback()
            except Exception as e:
                log.exception(f'WS run stop callbacks error: {e}')

        if not self.finished.is_set():
            self.finished.set()
