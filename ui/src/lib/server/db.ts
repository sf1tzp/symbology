import { Kysely, PostgresDialect } from 'kysely';
import pg from 'pg';
import type { DB } from './db/types';
import { getDatabaseUrl } from './db-config';

const { Pool } = pg;

const dialect = new PostgresDialect({
	pool: new Pool({
		connectionString: getDatabaseUrl(),
		max: 10
	})
});

export const db = new Kysely<DB>({ dialect });
