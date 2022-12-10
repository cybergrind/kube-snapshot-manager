from fastapi import APIRouter, FastAPI
from prometheus_client import Gauge
from starlette_exporter import handle_metrics, PrometheusMiddleware


root = APIRouter()
root.add_route('/metrics', handle_metrics)
UP = Gauge('up', 'Snapshot Manager is up', ['app'])
UP.labels(app='snapshot_manager').set(1)


def get_app() -> FastAPI:
    app = FastAPI()
    app.include_router(root)
    app.add_middleware(PrometheusMiddleware, app_name='snapshot_manager', skip_paths=['/metrics'])
    return app
