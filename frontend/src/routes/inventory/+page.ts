import { redirect } from '@sveltejs/kit';
import type { PageLoad } from './$types';

// The page moved to /items when it gained the warehouse and chests; old links keep working.
export const load: PageLoad = ({ url }) => {
	redirect(308, `/items${url.search}`);
};
