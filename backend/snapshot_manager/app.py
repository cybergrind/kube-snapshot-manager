from pathlib import Path
from fastapi import APIRouter, FastAPI, WebSocket
from prometheus_client import Gauge
from starlette_exporter import handle_metrics, PrometheusMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from .controller import Controller


UP = Gauge('up', 'Snapshot Manager is up', ['app'])
UP.labels(app='snapshot_manager').set(1)

root = APIRouter()
root.add_route('/metrics', handle_metrics)

@root.get('/')
async def index():
    return FileResponse(Path('./frontend/kube-snapshot-manager/build/index.html'))



@root.websocket('/api/ws')
async def ws(sock: WebSocket):
    await sock.accept()
    await sock.send_json({'type': 'echo'})
    volumes = await Controller().describe_volumes()
    await sock.send_json({'type': 'volumes', 'volumes': volumes})
    msg = await sock.receive_json()


def get_app() -> FastAPI:
    app = FastAPI()
    app.include_router(root)
    app.add_middleware(PrometheusMiddleware, app_name='snapshot_manager', skip_paths=['/metrics'])
    app.mount('/static', StaticFiles(directory=Path('./frontend/kube-snapshot-manager/build')), name='static')
    return app
