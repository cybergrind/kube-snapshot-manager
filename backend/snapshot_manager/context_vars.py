from contextvars import ContextVar

CONTROLLER = ContextVar('aws_controller', default=None)
KUBE_CONTROLLER1 = ContextVar('kube1_controller', default=None)
KUBE_CONTROLLER2 = ContextVar('kube2_controller', default=None)
ALL_KUBE_CLUSTERS = [KUBE_CONTROLLER1, KUBE_CONTROLLER2]
