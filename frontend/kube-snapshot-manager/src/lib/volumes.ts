export function betterName(volume) {
	if (volume.tags.length === 0) {
		return volume.id
	}
	if (!volume.tags['kubernetes.io/created-for/pvc/name']) {
		if (volume.tags['Name']) {
			return `${volume.id} / ${volume.tags['Name']}`
		}
		return volume.id
	}
	const namespace = volume.tags['kubernetes.io/created-for/pvc/namespace']
	const name = volume.tags['kubernetes.io/created-for/pvc/name']
	return `${namespace} / ${name}`
}
