from pathlib import Path
from pydantic import BaseSettings


class Config(BaseSettings):
    KUBECONFIG1: Path
    KUBECONFIG2: Path
