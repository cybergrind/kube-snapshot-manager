import logging
import asyncio
from asyncio import CancelledError, shield, Task
from typing import Optional


log = logging.getLogger(__name__)


class Controller:
    def __init__(self, retry_timeout=5, loop_interval=60):
        self.stopping = False
        self.retry_timeout = retry_timeout
        self.loop_interval = loop_interval
        self.stopping = False
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

    def on_error(self, exception):
        """
        return True if shoult stop
        do reinitialization here if required
        """
        log.exception(f'Exception in loop: {self}')

    async def start(self):
        await self.startup()
        self.active_loop = asyncio.ensure_future(self.inner_loop())
        return self.active_loop

    async def stop(self):
        self.stopping = True
        if self.active_loop:
            self.active_loop.cancel()
            await self.active_loop

    async def inner_loop(self):
        try:
            while not self.stopping:
                try:
                    await self.loop_iteration()
                    await asyncio.sleep(self.get_loop_interval())
                except CancelledError:
                    log.info(f'Cancelled loop: {self}')
                    break
                except Exception as e:
                    should_stop = self.on_error(e)
                    if should_stop:
                        log.info(f'Stopping loop because of error: {self}')
                        break
                    timeout = self.get_retry_timeout()
                    log.info(f'Retry in {timeout} seconds')
                    await asyncio.sleep(timeout)
        finally:
            # shielded
            self.stopping = True
            await shield(self.shutdown())
