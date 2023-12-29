import pytest
import time
from snapshot_manager.generic.controller import Timer


class TestTimer:
    async def test_basic_functionality(self):
        now = time.time()
        timer = Timer(None)
        await timer.wait(0.03)
        assert pytest.approx(time.time() - now, 0.01) == 0.03
