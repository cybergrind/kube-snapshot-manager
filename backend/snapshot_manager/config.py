from pathlib import Path
from pydantic import BaseSettings


class Config(BaseSettings):
    KUBECONFIG: Path
