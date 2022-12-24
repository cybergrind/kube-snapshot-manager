import logging

import aioboto3


log = logging.getLogger('controller')


class Controller:
    def __init__(self):
        self.session = aioboto3.Session()
        self.ec2_resource = self.session.resource('ec2')
        self._cached_volumes = None
        self._cached_snapshots = None

    async def volume_to_dict(self, volume):
        attachments = await volume.attachments
        for attachment in attachments:
            attachment['AttachTime'] = attachment['AttachTime'].isoformat()
        tags = {tag['Key']: tag['Value'] for tag in (await volume.tags) or []}
        return {
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

    async def get_volume_snapshots(self, volume_id):
        resp = []
        async for snapshot in self.ec2.snapshots.filter(
            Filters=[{'Name': 'volume-id', 'Values': [volume_id]}]
        ):
            resp.append(
                {
                    'id': snapshot.id,
                    'state': await snapshot.state,
                    'volume_id': await snapshot.volume_id,
                    'start_time': (await snapshot.start_time).strftime('%Y-%m-%d %H:%M:%S'),
                    'progress': await snapshot.progress,
                    'tags': await snapshot.tags,
                }
            )
        return resp

    async def describe_volumes(self):
        if self._cached_volumes is None:
            resp = {}
            async for volume in self.ec2.volumes.all():
                data = await self.volume_to_dict(volume)
                resp[volume.id] = data
            self._cached_volumes = resp
        return self._cached_volumes

    async def describe_snapshots(self):
        if self._cached_snapshots is None:
            resp = {}
            # only owned snapshots
            async for snapshot in self.ec2.snapshots.filter(OwnerIds=['self']):
                data = await self.snapshot_to_dict(snapshot)
                resp[snapshot.id] = data
                self._cached_snapshots = resp
        return self._cached_snapshots

    async def snapshot_to_dict(self, snapshot):
        tags = {tag['Key']: tag['Value'] for tag in (await snapshot.tags) or []}
        return {
            'id': snapshot.id,
            'state': await snapshot.state,
            'volume_id': await snapshot.volume_id,
            'size': await snapshot.volume_size,
            'start_time': (await snapshot.start_time).strftime('%Y-%m-%d %H:%M:%S'),
            'progress': await snapshot.progress,
            'description': await snapshot.description,
            'tags': tags,
        }

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
