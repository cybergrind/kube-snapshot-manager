import logging
import asyncio
from asyncio import CancelledError, shield, Task
from typing import Optional


log = logging.getLogger(__name__)


class Controller:
    def __init__(self, retry_timeout=5, loop_interval=60, loop_timeout=120):
        self.stopping = False
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
        self.stopping = False
        await self.startup()
        self.active_loop = asyncio.ensure_future(self.inner_loop())
        return self.active_loop

    async def stop(self):
        self.stopping = True
        if self.active_loop:
            self.active_loop.cancel()
            await self.active_loop

    async def _call_on_error(self, error) -> bool:
        should_stop = False
        try:
            should_stop = bool(await self.on_error(error))
        except Exception as e:
            log.exception(f'Exception in on_error handler: {e}')
        return should_stop

    async def inner_loop(self):
        try:
            while not self.stopping:
                try:
                    await asyncio.wait_for(self.loop_iteration(), timeout=self.loop_timeout)
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
                    timeout = self.get_retry_timeout()
                    log.info(f'Retry in {timeout} seconds')
                    await asyncio.sleep(timeout)
        finally:
            # shielded
            log.debug(f'Shielded shutdown in finally {self.stopping=}')
            if self.active_loop:
                log.debug(f'is_cancelled={self.active_loop.cancelled()}')
            self.stopping = True
            await shield(self.shutdown())
