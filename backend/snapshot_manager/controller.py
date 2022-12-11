import logging

import aioboto3


log = logging.getLogger('controller')


class Controller:
    def __init__(self):
        self.session = aioboto3.Session()
        self.ec2_resource = self.session.resource('ec2')

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
        resp = {}
        async for volume in self.ec2.volumes.all():
            data = await self.volume_to_dict(volume)
            resp[volume.id] = data
        return resp

    async def startup(self):
        log.debug('startup...')
        self.ec2 = await self.ec2_resource.__aenter__()
        log.debug(f'EC2: {self.ec2}')

    async def shutdown(self):
        log.debug('shutting down...')
        await self.ec2_resource.__aexit__(None, None, None)
