import asyncio
import enum
import logging

from asyncio import CancelledError, Task, shield
from typing import Callable, List, Optional

from snapshot_manager.generic.debug import DEBUG_GLOBAL, DebugObject


log = logging.getLogger(__name__)


class State(enum.Enum):
    STARTING = 'starting'
    CALLBACK = 'callback'
    SLEEP = 'sleep'
    BACKOFF = 'backoff'
    ON_ERROR = 'on_error'
    STOPPING = 'stopping'
    STOPPED = 'stopped'


class Timer:
    def __init__(self, parent):
        self.parent = parent
        self.wait_event = asyncio.Event()
        self.wait_task: Optional[Task] = None

    def wait(self, timeout: int | float):
        if self.wait_task and not self.wait_task.done():
            raise RuntimeError('Already waiting')

        self.wait_event.clear()
        self.wait_task = asyncio.create_task(self._wait(timeout))

        return self.wait_event.wait()

    async def _wait(self, timeout: int | float):
        await asyncio.sleep(timeout)
        if not self.wait_event.is_set():
            self.wait_event.set()

    def trigger(self):
        if not self.wait_event.is_set():
            if self.wait_task and not self.wait_task.done():
                self.wait_task.cancel()
            self.wait_event.set()


class Controller:
    stop_states = {State.STOPPING, State.STOPPED}

    def __init__(self, retry_timeout=5, loop_interval=60, loop_timeout=120, debug=False):
        self.state = State.STOPPED
        self.retry_timeout = retry_timeout
        self.loop_interval = loop_interval
        self.loop_timeout = loop_timeout
        self.active_loop: Optional[Task] = None
        self.timer = Timer(self)
        self.on_stop: List[Callable] = []

        self.debug: Optional[DebugObject] = None
        if debug:
            name = getattr(self, 'name', f'{self.__class__.__name__}_{id(self)}')
            if isinstance(debug, DebugObject):
                self.debug = DebugObject(parent=debug, name=name)
            else:
                self.debug = DebugObject(parent=DEBUG_GLOBAL.get(), name=name)

            if self.debug:
                self.on_stop.append(lambda: self.debug.parent.remove_child(self.debug))

    def set_state(self, value):
        log.debug(f'{self} state changed: {self.state} -> {value}')
        self.state = value
        if self.debug:
            self.debug.track('state', str(value))

    async def startup(self):
        pass

    async def shutdown(self):
        pass

    async def loop_iteration(self):
        """
        do job here
        """

    def get_retry_timeout(self):
        return self.retry_timeout

    def get_loop_interval(self):
        return self.loop_interval

    async def on_error(self, exception) -> Optional[bool]:
        """
        return True if shoult stop
        do reinitialization here if required
        """
        log.exception(f'Exception in loop: {self} {exception}')

    async def start(self):
        if self.state != State.STOPPED:
            raise RuntimeError(f'Cannot start {self} in state {self.state}')

        self.state = State.STARTING
        await self.startup()
        self.active_loop = asyncio.ensure_future(self.inner_loop())
        return self.active_loop

    async def stop(self):
        if self.active_loop:
            self.active_loop.cancel()
            await self.active_loop

    @property
    def is_running(self):
        return self.state not in self.stop_states

    async def inner_loop(self):
        try:
            while self.is_running:
                try:
                    self.set_state(State.CALLBACK)
                    await asyncio.wait_for(self.loop_iteration(), timeout=self.loop_timeout)
                    self.set_state(State.SLEEP)
                    await self.timer.wait(self.get_loop_interval())
                except CancelledError:
                    log.debug(f'Cancelled loop: {self}')
                    break
                except Exception as e:
                    log.debug('check should_stop')
                    should_stop = await self._call_on_error(e)
                    if should_stop:
                        log.info(f'Stopping loop because of error: {self}')
                        break
                    self.set_state(State.BACKOFF)
                    timeout = self.get_retry_timeout()
                    log.info(f'Retry in {timeout} seconds')
                    await self.timer.wait(timeout)
        finally:
            # stopping => shutdown() => stopped
            log.debug(f'Shielded shutdown in finally {self.state=}')
            await self._do_shutdown()

    async def _call_on_error(self, error) -> bool:
        self.set_state(State.ON_ERROR)
        should_stop = False
        try:
            should_stop = bool(await self.on_error(error))
        except Exception as e:
            log.exception(f'Exception in on_error handler: {e}')
        return should_stop

    async def _do_shutdown(self):
        if self.active_loop:
            log.debug(f'is_cancelled={self.active_loop.cancelled()}')
        self.set_state(State.STOPPING)

        try:
            log.info(f'shielded shutdown {self=}')
            await shield(self.shutdown())
            for callback in self.on_stop:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await shield(callback())
                    else:
                        callback()
                except Exception as e:
                    log.exception(f'Exception in on_stop callback: {e}')
        except Exception as e:
            log.exception(f'Exception in shutdown: {e}')
        finally:
            self.set_state(State.STOPPED)
