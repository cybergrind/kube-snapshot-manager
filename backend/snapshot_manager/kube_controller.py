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
                    namespace=pv.spec.claim_ref.namespace,
                    capacity=pv.spec.capacity['storage'],
                    access_modes=pv.spec.access_modes,
                    reclaim_policy=pv.spec.persistent_volume_reclaim_policy,
                    volume_mode=pv.spec.volume_mode,
                    status=pv.status.phase,
                    claim=pv.spec.claim_ref.name if pv.spec.claim_ref else '',
                    storage_class=pv.spec.storage_class_name,
                    volume=pv.spec.csi.volume_handle,
                )
            )
        return out

    async def get_pv_byid(self, pvid) -> PV | None:
        pv_list = await self.get_pvs()
        for pv in pv_list:
            if pv.name == pvid:
                return pv

    async def create_pv_snapshot(self, pvid: str, snapshot_name: str):
        pv = await self.get_pv_byid(pvid)
        if not pv:
            log.info(f'PV {pvid} not found')
            return

        log.debug(f'Creating snapshot {snapshot_name} for {pvid}')

        # create snapshot with CRD
        crd = client.CustomObjectsApi(self.api)
        ns = pv.namespace
        snapshot_class = 'ebs-csi-aws'
        description = 'kube-controller-snapshot'
        await crd.create_namespaced_custom_object(
            group='snapshot.storage.k8s.io',
            version='v1',
            namespace=ns,
            plural='volumesnapshots',
            body={
                'apiVersion': 'snapshot.storage.k8s.io/v1',
                'kind': 'VolumeSnapshot',
                'metadata': {'name': snapshot_name, 'namespace': ns},
                'spec': {
                    'volumeSnapshotClassName': snapshot_class,
                    'source': {'persistentVolumeClaimName': pv.claim},
                    'description': description,
                },
            },
        )

    async def get_snapshot_by_snapid(self, snap_id: str):
        """
        snap_id: snapshot id in AWS, should be in content
        """
        log.debug(f'Getting snapshot {snap_id}')
        crd = client.CustomObjectsApi(self.api)
        content = await self.get_snap_content_by_handle(snap_id)
        if not content:
            log.info(f'Content not found for {snap_id}')
            return

        # list for all namespaces
        snapshots = await crd.list_cluster_custom_object(
            group='snapshot.storage.k8s.io', version='v1', plural='volumesnapshots'
        )
        for snapshot in snapshots['items']:
            if snapshot['status']['boundVolumeSnapshotContentName'] == content['metadata']['name']:
                log.debug(f'Got snapshot: {snapshot=}')
                return snapshot

    async def get_snap_content_by_handle(self, snap_id: str):
        crd = client.CustomObjectsApi(self.api)
        snap_contents = await crd.list_cluster_custom_object(
            group='snapshot.storage.k8s.io', version='v1', plural='volumesnapshotcontents'
        )
        for content in snap_contents['items']:
            if content['status']['snapshotHandle'] == snap_id:
                return content

    async def delete_snapshot_by_snapid(self, snap_id: str):
        snap = await self.get_snapshot_by_snapid(snap_id)
        if not snap:
            log.info(f'Snapshot {snap_id} not found')
            return
        crd = client.CustomObjectsApi(self.api)
        await crd.delete_namespaced_custom_object(
            group='snapshot.storage.k8s.io',
            version='v1',
            namespace=snap['metadata']['namespace'],
            plural='volumesnapshots',
            name=snap['metadata']['name'],
            body=client.V1DeleteOptions(),
        )

    async def shutdown(self):
        pass
