import logging
from asyncio import Queue
from pathlib import Path
from typing import Callable, Optional

import aioboto3
from pydantic import BaseModel

from .models import SnaphotsEvent, Snapshot, Snapshots, Volume, Volumes, VolumesEvent


log = logging.getLogger('controller')
cache = Path('.cache')
cache.mkdir(exist_ok=True)


class Controller:
    def __init__(self, volumes=None, snapshots=None, cache_dir=cache):
        self.session = aioboto3.Session()
        self.ec2_resource = self.session.resource('ec2')
        self._cached_volumes: Optional[Volumes] = volumes
        self._cached_snapshots: Optional[Snapshots] = snapshots
        self._volumes_file = cache_dir / 'volumes.json'
        self._snapshots_file = cache_dir / 'snapshots.json'
        self.subscribers = {}

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

    def load_cached(self):
        if self._cached_volumes is not None:
            log.debug('volumes already cached or provided')
            return
        if not self._volumes_file.exists():
            log.debug(f'no cache file: {self._volumes_file}')
            return
        log.debug('Load from cache')
        self._cached_volumes = Volumes.parse_raw(self._volumes_file.read_text())
        self._cached_snapshots = Snapshots.parse_raw(self._snapshots_file.read_text())

    def save_cache(self):
        log.debug('saving cache...')
        if self._cached_volumes:
            self._volumes_file.write_text(self._cached_volumes.json())
        if self._cached_snapshots:
            self._snapshots_file.write_text(self._cached_snapshots.json())

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

    async def describe_volumes(self) -> Volumes:
        if self._cached_volumes is None:
            resp = {}
            async for volume in self.ec2.volumes.all():
                data = await self.volume_to_dict(volume)
                resp[volume.id] = data
            resp = Volumes(__root__=resp)
            self._cached_volumes = resp
        self.publish(VolumesEvent(volumes=self._cached_volumes))
        return self._cached_volumes

    async def describe_snapshots(self) -> Snapshots:
        if not self._cached_snapshots:
            resp = {}
            async for snapshot in self.ec2.snapshots.filter(OwnerIds=['self']):
                data = await self.snapshot_to_dict(snapshot)
                resp[snapshot.id] = data

            resp = Snapshots(__root__=resp)
            self._cached_snapshots = resp
            self.save_cache()
        self.publish(SnaphotsEvent(snapshots=self._cached_snapshots))
        return self._cached_snapshots

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
        self.load_cached()
        self.ec2 = await self.ec2_resource.__aenter__()
        log.debug(f'EC2: {self.ec2}')

    async def shutdown(self):
        log.debug('shutting down...')
        self.save_cache()
        await self.ec2_resource.__aexit__(None, None, None)
