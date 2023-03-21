import logging
from asyncio import Queue
from pathlib import Path
from typing import Callable, TYPE_CHECKING

import aioboto3
from pydantic import BaseModel

from fan_tools.python import cache_async as cache

from .models import SnaphotsEvent, Snapshot, Snapshots, Volume, Volumes, VolumesEvent


if TYPE_CHECKING:
    from snapshot_manager.kube_controller import KubeController


log = logging.getLogger('controller')
cache_dir = Path('.cache')
cache_dir.mkdir(exist_ok=True)


class AWSController:
    def __init__(self, volumes=None, snapshots=None, cache_dir=cache_dir):
        self.session = aioboto3.Session()
        self.ec2_resource = self.session.resource('ec2')

        self._volumes_file = cache_dir / 'volumes.json'
        self.aws_describe_volumes = cache[type(Volumes)](self._volumes_file, Volumes, {})(
            self._aws_describe_volumes
        )

        self._snapshots_file = cache_dir / 'snapshots.json'
        self.aws_describe_snapshots = cache[type(Snapshots)](self._snapshots_file, Snapshots, {})(
            self._aws_describe_snapshots
        )

        self.subscribers = {}
        self.clusters = {}

    def add_cluster(self, cluster: 'KubeController'):
        self.clusters[cluster.name] = cluster

    def subscribe(self, queue: Queue) -> Callable:
        self.subscribers[queue] = queue

        def unsubscribe():
            if queue in self.subscribers:
                del self.subscribers[queue]

        return unsubscribe

    def publish(self, event: BaseModel):
        for q in self.subscribers:
            log.debug(f'Publish to WS-queue: {event.event} / {id(q)}')
            q.put_nowait(event)

    async def volume_to_dict(self, volume) -> Volume:
        attachments = await volume.attachments
        for attachment in attachments:
            attachment['AttachTime'] = attachment['AttachTime'].isoformat()
        tags = {tag['Key']: tag['Value'] for tag in (await volume.tags) or []}
        return Volume(
            **{
                'id': volume.id,
                'state': await volume.state,
                'size': await volume.size,
                'volume_type': await volume.volume_type,
                'create_time': (await volume.create_time).strftime('%Y-%m-%d %H:%M:%S'),
                'tags': tags,
                'iops': await volume.iops,
                'snapshot_id': await volume.snapshot_id,
                'availability_zone': await volume.availability_zone,
                'attachments': attachments,
                'snapshots': await self.get_volume_snapshots(volume.id),
            }
        )

    async def get_volume_snapshots(self, volume_id) -> list[Snapshot]:
        resp = []
        async for snapshot in self.ec2.snapshots.filter(
            Filters=[{'Name': 'volume-id', 'Values': [volume_id]}]
        ):
            tags = {tag['Key']: tag['Value'] for tag in (await snapshot.tags) or {}}
            resp.append(
                Snapshot(
                    **{
                        'description': await snapshot.description,
                        'id': snapshot.id,
                        'progress': await snapshot.progress,
                        'size': await snapshot.volume_size,
                        'start_time': (await snapshot.start_time).strftime('%Y-%m-%d %H:%M:%S'),
                        'state': await snapshot.state,
                        'tags': tags,
                        'volume_id': await snapshot.volume_id,
                    }
                )
            )
        return resp

    async def _aws_describe_volumes(self) -> Volumes:
        log.debug('AWS describe volumes')
        resp = {}
        async for volume in self.ec2.volumes.all():
            data = await self.volume_to_dict(volume)
            resp[volume.id] = data
        resp = Volumes(__root__=resp)
        return resp

    async def describe_volumes(self) -> Volumes:
        resp = await self.aws_describe_volumes()
        self.publish(VolumesEvent(volumes=resp))
        return resp

    async def _aws_describe_snapshots(self) -> Snapshots:
        log.debug('AWS describe snapshots')
        resp = {}
        snaps_by_cluster = {}
        for name, cluster in self.clusters.items():
            snaps_by_cluster[name] = await cluster.snapshots_by_snapid()

        async for snapshot in self.ec2.snapshots.filter(OwnerIds=['self']):
            data = await self.snapshot_to_dict(snapshot)
            resp[snapshot.id] = data
            for name, snaps in snaps_by_cluster.items():
                if snapshot.id in snaps:
                    data.clusters.append(f'{name}::{snaps[snapshot.id]["deletion_policy"]}')

        resp = Snapshots(__root__=resp)
        return resp

    async def describe_snapshots(self) -> Snapshots:
        resp = await self.aws_describe_snapshots()
        self.publish(SnaphotsEvent(snapshots=resp))
        return resp

    async def snapshot_to_dict(self, snapshot) -> Snapshot:
        tags = {tag['Key']: tag['Value'] for tag in (await snapshot.tags) or {}}
        return Snapshot(
            **{
                'description': await snapshot.description,
                'id': snapshot.id,
                'progress': await snapshot.progress,
                'size': await snapshot.volume_size,
                'start_time': (await snapshot.start_time).strftime('%Y-%m-%d %H:%M:%S'),
                'state': await snapshot.state,
                'tags': tags,
                'volume_id': await snapshot.volume_id,
            }
        )

    async def snapshot_volume(self, volume_id):
        volume = self.ec2.Volume(volume_id)
        snapshot = await volume.create_snapshot()
        return snapshot.id

    async def startup(self):
        log.debug('startup...')
        self.ec2 = await self.ec2_resource.__aenter__()
        log.debug(f'EC2: {self.ec2}')

    async def shutdown(self):
        log.debug('shutting down...')
        await self.ec2_resource.__aexit__(None, None, None)
