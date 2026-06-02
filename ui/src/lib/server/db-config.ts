import { env } from '$env/dynamic/private';

/**
 * Builds the Postgres connection string from env, shared by the Kysely app
 * pool (`db.ts`) and the Better Auth pool (`auth.ts`). Both point at the same
 * database; Better Auth scopes its tables to the `auth` schema via search_path.
 */
export function getDatabaseUrl(): string {
	if (env.DATABASE_URL) return env.DATABASE_URL;

	const host = env.DATABASE_HOST ?? 'localhost';
	const port = env.DATABASE_PORT ?? '5432';
	const user = env.DATABASE_USER ?? 'postgres';
	const password = env.DATABASE_PASSWORD ?? 'postgres';
	const name = env.DATABASE_NAME ?? 'symbology';
	return `postgresql://${user}:${password}@${host}:${port}/${name}`;
}
