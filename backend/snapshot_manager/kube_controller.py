import logging
from pathlib import Path

from kubernetes_asyncio import client, config
from kubernetes_asyncio.client.api_client import ApiClient

from .models import PV


log = logging.getLogger(__name__)


class KubeController:
    def __init__(self, config_path: Path, name: str):
        self.name = name
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
                },
            },
        )

    async def snapshots_by_snapid(self):
        """
        get all snaphots content and map
        snap_id => VolumeSnapshot
        """
        crd = client.CustomObjectsApi(self.api)
        contents = await crd.list_cluster_custom_object(
            group='snapshot.storage.k8s.io', version='v1', plural='volumesnapshotcontents'
        )
        snapshots = await crd.list_cluster_custom_object(
            group='snapshot.storage.k8s.io', version='v1', plural='volumesnapshots'
        )
        # snapshot['status']['boundVolumeSnapshotContentName'] == content['metadata']['name']
        # snap_id == content['status']['snapshotHandle']
        # snap_id => snapshot
        name_to_content = {}
        for content in contents['items']:
            name_to_content[content['metadata']['name']] = content
        snap_id_to_snapshot = {}
        for snapshot in snapshots['items']:
            content = name_to_content[snapshot['status']['boundVolumeSnapshotContentName']]
            snap_id_to_snapshot[content['status']['snapshotHandle']] = snapshot
            snapshot['content'] = content
            snapshot['deletion_policy'] = content['spec']['deletionPolicy']
        return snap_id_to_snapshot

    async def get_snapshot_by_snapid(self, snap_id: str):
        """
        snap_id: snapshot id in AWS, should be in content
        """
        log.debug(f'Getting snapshot {snap_id}')
        snap_id_to_snapshot = await self.snapshots_by_snapid()
        return snap_id_to_snapshot.get(snap_id)

    async def delete_snapshot_by_snapid(self, snap_id: str):
        """
        snap_id: snapshot id in AWS, should be in content
        """
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
