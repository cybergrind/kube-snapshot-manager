import asyncio

from fastapi import WebSocket

from snapshot_manager.generic.controller import Controller


class WSController(Controller):
    def __init__(self, ws: WebSocket, *args, **kwargs):
        self.ws = ws
        self.finished = asyncio.Event()
        super().__init__(*args, **kwargs)

    async def send_debug(self, sections={}):
        pass
