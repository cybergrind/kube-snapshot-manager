import aioboto3


class Controller:
    def __init__(self):
        self.session = aioboto3.Session()
        self.ec2 = self.session.resource('ec2')

    async def volume_to_dict(self, volume):
        return {
            'id': volume.id,
            'state': await volume.state,
            'size': await volume.size,
            'volume_type': await volume.volume_type,
            'create_time': (await volume.create_time).strftime('%Y-%m-%d %H:%M:%S'),
            'tags': await volume.tags,
            'iops': await volume.iops,
            'snapshot_id': await volume.snapshot_id,
            'availability_zone': await volume.availability_zone,
            #'attachments': await volume.attachments,
        }

    async def describe_volumes(self):
        async with self.ec2 as cli:
            resp = {}
            async for volume in cli.volumes.all():
                data = await self.volume_to_dict(volume)
                resp[volume.id] = data
                print(f'{data=}')
            return resp
