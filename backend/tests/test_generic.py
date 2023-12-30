import pytest
import time
from snapshot_manager.generic.controller import Timer
from snapshot_manager.generic.debug import DebugObject


class TestTimer:
    async def test_basic_functionality(self):
        now = time.time()
        timer = Timer(None)
        await timer.wait(0.03)
        assert pytest.approx(time.time() - now, 0.01) == 0.03


class TestDebugObject:
    def test_generic(self):
        g = DebugObject(None)
        c1 = DebugObject(g, name='kube1')
        c1.track('state', 'test')
        c2 = DebugObject(g, name='kube2')
        assert g.serialize() == {
            'kube1': {'values': {'state': 'test'}, 'buttons': {}},
            'kube2': {'values': {}, 'buttons': {}},
        }
