from pydantic import BaseModel


class Snapshot(BaseModel):
    id: str
    state: str
    volume_id: str
    size: int
    start_time: str
    progress: str
    description: str
    tags: dict


class Snapshots(BaseModel):
    __root__: dict[str, Snapshot]


class SnaphotsEvent(BaseModel):
    event: str = 'snapshots'
    snapshots: Snapshots


class Volume(BaseModel):
    id: str
    state: str
    size: int
    volume_type: str
    create_time: str
    tags: dict
    iops: int
    snapshot_id: str
    availability_zone: str
    attachments: list[dict]
    snapshots: list[Snapshot]


class Volumes(BaseModel):
    __root__: dict[str, Volume]


class VolumesEvent(BaseModel):
    event: str = 'volumes'
    volumes: Volumes


class PV(BaseModel):
    name: str
    namespace: str
    capacity: str
    access_modes: list[str]
    reclaim_policy: str
    volume_mode: str
    status: str
    claim: str
    storage_class: str
    volume: str
