from fastapi import APIRouter, FastAPI, WebSocket
from prometheus_client import Gauge
from starlette_exporter import handle_metrics, PrometheusMiddleware


UP = Gauge('up', 'Snapshot Manager is up', ['app'])
UP.labels(app='snapshot_manager').set(1)

root = APIRouter()
root.add_route('/metrics', handle_metrics)



@root.websocket('/api/ws')
async def ws(sock: WebSocket):
    await sock.accept()
    await sock.send_json({'type': 'echo'})


def get_app() -> FastAPI:
    app = FastAPI()
    app.include_router(root)
    app.add_middleware(PrometheusMiddleware, app_name='snapshot_manager', skip_paths=['/metrics'])
    return app
