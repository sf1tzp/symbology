import { Kysely, PostgresDialect } from 'kysely';
import pg from 'pg';
import { env } from '$env/dynamic/private';
import type { DB } from './db/types';

const { Pool } = pg;

function getDatabaseUrl(): string {
	if (env.DATABASE_URL) return env.DATABASE_URL;

	const host = env.DATABASE_HOST ?? 'localhost';
	const port = env.DATABASE_PORT ?? '5432';
	const user = env.DATABASE_USER ?? 'postgres';
	const password = env.DATABASE_PASSWORD ?? 'postgres';
	const name = env.DATABASE_NAME ?? 'symbology';
	return `postgresql://${user}:${password}@${host}:${port}/${name}`;
}

const dialect = new PostgresDialect({
	pool: new Pool({
		connectionString: getDatabaseUrl(),
		max: 10
	})
});

export const db = new Kysely<DB>({ dialect });
