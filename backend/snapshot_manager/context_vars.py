from contextvars import ContextVar
import typing
from typing import Optional

if typing.TYPE_CHECKING:
    from .kube_controller import KubeController
    from .controller import AWSController


CONTROLLER: ContextVar[Optional['AWSController']] = ContextVar('aws_controller', default=None)
KUBE_CONTROLLER1: ContextVar[Optional['KubeController']] = ContextVar(
    'kube1_controller', default=None
)
KUBE_CONTROLLER2: ContextVar[Optional['KubeController']] = ContextVar(
    'kube2_controller', default=None
)
ALL_KUBE_CLUSTERS = [KUBE_CONTROLLER1, KUBE_CONTROLLER2]
