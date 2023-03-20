from pathlib import Path

from pydantic import BaseSettings
from snapshot_manager import logs  # noqa


class Config(BaseSettings):
    KUBECONFIG1: Path
    KUBECONFIG2: Path
