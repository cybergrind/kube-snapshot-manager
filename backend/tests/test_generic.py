import asyncio
import time

from unittest.mock import AsyncMock

import pytest

from snapshot_manager.generic.controller import Timer
from snapshot_manager.generic.debug import DebugObject


class TestTimer:
    async def test_basic_functionality(self):
        now = time.time()
        timer = Timer(None)
        await timer.wait(0.03)
        assert pytest.approx(time.time() - now, 0.01) == 0.03

    async def test_trigger(self, event_loop):
        now = time.time()
        timer = Timer(None)
        event_loop.call_later(0, timer.trigger)
        await timer.wait(3)
        assert time.time() - now <= 0.1

    async def test_wait_for(self):
        now = time.time()
        timer = Timer(None)
        mm = AsyncMock()
        wf = timer.wait_for(mm(), 3)
        await asyncio.sleep(0.01)
        mm.assert_not_awaited()
        await wf
        assert time.time() - now <= 0.1
        mm.assert_awaited()

    async def test_mutiwait(self):
        timer = Timer(None)
        with pytest.raises(RuntimeError):
            await asyncio.gather(timer.wait(0.01), timer.wait(0.02))

    async def test_join(self):
        now = time.time()
        timer = Timer(None)
        await asyncio.gather(timer.wait(0.01), timer.join())
        assert pytest.approx(time.time() - now, 0.1) == 0.01


class TestDebugObject:
    def test_generic(self):
        g = DebugObject(None)
        c1 = DebugObject(g, name='kube1')
        c1.track('state', 'test')
        DebugObject(g, name='kube2')
        resp = g.serialize()
        for name, val in resp.items():
            if 'timestamp' in val['values']:
                del val['values']['timestamp']
        assert resp == {
            'global': {'buttons': {}, 'values': {'change_callbacks': 0, 'children': 2}},
            'kube1': {'values': {'state': 'test'}, 'buttons': {}},
            'kube2': {'values': {}, 'buttons': {}},
        }
