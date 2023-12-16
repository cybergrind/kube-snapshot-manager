```bash

aws ec2 describe-volumes

aws ec2 describe-snapshots --owner-ids self
```


[PV.spec.claimRef](https://stackoverflow.com/questions/34282704/can-a-pvc-be-bound-to-a-specific-pv/34323691#34323691)


### TODO

* snapshot details:
 * events: after VolumeSnapshot created => wait for snapshot created
 * events: triggered creation / progress != 100 => loop with refresh + fill tags
 * events: after creation / progress become 100 => trigger refresh cache/ui
 * aws: should allow deletion of snapshot (if there is attached VolumeSnapshot - it should be deleted first)


* generic controller
 * better timeouts - support dynamic trigger. eg. change implementation to asyncio.Event + asyncio.sleep
 * current controller state (start, callback, on_error, sleep, stopping, stopped)
 * log with controller name
 * simple controller factory: name, callback
 * metrics
 * generic alerts

* small state machine

* debug screen
 * dynamically register debug values (number of messages, current timeout) + buttons (restart, etc)
 * add svelte component to debug values
 * hierarchically group display values and buttons
 * maybe historical values (+graph)
 * timing for loop iteration
 * timing since last iteration
