import logging
import asyncio
from asyncio import CancelledError, shield, Task
from typing import Optional
import enum


log = logging.getLogger(__name__)


class State(enum.Enum):
    STARTING = 'starting'
    CALLBACK = 'callback'
    SLEEP = 'sleep'
    BACKOFF = 'backoff'
    ON_ERROR = 'on_error'
    STOPPING = 'stopping'
    STOPPED = 'stopped'


class Controller:
    stop_states = {State.STOPPING, State.STOPPED}

    def __init__(self, retry_timeout=5, loop_interval=60, loop_timeout=120):
        self.state = State.STOPPED
        self.retry_timeout = retry_timeout
        self.loop_interval = loop_interval
        self.loop_timeout = loop_timeout
        self.active_loop: Optional[Task] = None

    async def startup(self):
        pass

    async def shutdown(self):
        pass

    async def loop_iteration(self):
        """
        do job here
        """
        pass

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
                    self.state = State.CALLBACK
                    await asyncio.wait_for(self.loop_iteration(), timeout=self.loop_timeout)
                    self.state = State.SLEEP
                    await asyncio.sleep(self.get_loop_interval())
                except CancelledError:
                    log.debug(f'Cancelled loop: {self}')
                    break
                except Exception as e:
                    log.debug('check should_stop')
                    should_stop = await self._call_on_error(e)
                    if should_stop:
                        log.info(f'Stopping loop because of error: {self}')
                        break
                    self.state = State.BACKOFF
                    timeout = self.get_retry_timeout()
                    log.info(f'Retry in {timeout} seconds')
                    await asyncio.sleep(timeout)
        finally:
            # stopping => shutdown() => stopped
            log.debug(f'Shielded shutdown in finally {self.state=}')
            await self._do_shutdown()

    async def _call_on_error(self, error) -> bool:
        self.state = State.ON_ERROR
        should_stop = False
        try:
            should_stop = bool(await self.on_error(error))
        except Exception as e:
            log.exception(f'Exception in on_error handler: {e}')
        return should_stop

    async def _do_shutdown(self):
        if self.active_loop:
            log.debug(f'is_cancelled={self.active_loop.cancelled()}')
        self.state = State.STOPPING
        try:
            await shield(self.shutdown())
        except Exception as e:
            log.exception(f'Exception in shutdown: {e}')
        finally:
            self.state = State.STOPPED