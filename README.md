
```bash

aws ec2 describe-volumes

aws ec2 describe-snapshots --owner-ids self
```


[PV.spec.claimRef](https://stackoverflow.com/questions/34282704/can-a-pvc-be-bound-to-a-specific-pv/34323691#34323691)


### TODO

* snapshot details:
 * should allow changing retention policy
 * kube: should allow deletion of VolumeSnapshot
 * aws: should allow deletion of snapshot (if there is attached VolumeSnapshot - it should be deleted first)



