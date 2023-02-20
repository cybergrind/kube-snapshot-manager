import type { PageLoad } from './$types'

export const load = (({ params }) => {
	const { slug } = params
	return { slug }
}) satisfies PageLoad
