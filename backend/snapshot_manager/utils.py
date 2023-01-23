import logging
from functools import wraps
from pathlib import Path
from typing import Awaitable, Callable, ParamSpec, Type

from pydantic import BaseModel


log = logging.getLogger(__name__)
P = ParamSpec('P')
FuncSpec = Callable[P, Awaitable[BaseModel]]


class cache:
    def __init__(self, fname: Path, model: Type[BaseModel], default: BaseModel):
        self.fname = fname
        self._default = default
        self.cache = default
        # load from file
        if self.fname.exists():
            self.cache = model.parse_file(self.fname)

    def __call__(self, func: FuncSpec) -> FuncSpec:
        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> BaseModel:
            if self.cache:
                return self.cache
            value = await func(*args, **kwargs)
            self.cache = value
            self.fname.write_text(self.cache.json())
            return value

        return wrapper

    def reset_cache(self):
        self.cache = self._default
        self.fname.unlink()
