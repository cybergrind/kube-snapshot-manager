import logging
from pathlib import Path

from kubernetes_asyncio import client, config
from kubernetes_asyncio.client.api_client import ApiClient

from .models import PV


log = logging.getLogger(__name__)


class KubeController:
    def __init__(self, config_path: Path):
        assert config_path.exists(), f'Config file {config_path} does not exist'
        self.config_path = config_path

    async def startup(self):
        self.config = client.Configuration()
        await config.load_kube_config(
            config_file=str(self.config_path), client_configuration=self.config
        )
        self.api_client = ApiClient(self.config)
        self.api = await self.api_client.__aenter__()

        v1 = client.CoreV1Api(self.api)
        pods = await v1.list_namespaced_pod('octo-prod')
        for pod in pods.items:
            log.debug(
                f'ip={pod.status.pod_ip} name={pod.metadata.name}, namespace={pod.metadata.namespace}'
            )
        await self.get_pvs()

    async def get_pvs(self) -> list[PV]:
        v1 = client.CoreV1Api(self.api)
        pv_list = await v1.list_persistent_volume()
        out = []
        for pv in pv_list.items:
            log.debug(
                f'pv={pv.metadata.name} status={pv.status.phase} pvc={pv.spec.claim_ref.name}'
            )
            out.append(
                PV(
                    name=pv.metadata.name,
                    capacity=pv.spec.capacity['storage'],
                    access_modes=pv.spec.access_modes,
                    reclaim_policy=pv.spec.persistent_volume_reclaim_policy,
                    volume_mode=pv.spec.volume_mode,
                    status=pv.status.phase,
                    claim=pv.spec.claim_ref.name if pv.spec.claim_ref else None,
                    storage_class=pv.spec.storage_class_name,
                    volume=pv.spec.csi.volume_handle,
                )
            )
        return out

    async def shutdown(self):
        pass
