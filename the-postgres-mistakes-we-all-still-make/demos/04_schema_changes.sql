-- 04_schema_changes.sql
-- Mistake: we change schemas by hand, during the day, with no lock_timeout.
--
-- ALTER TABLE orders ADD COLUMN note text;   -- needs ACCESS EXCLUSIVE for a moment,
--                                            -- but waits behind every current lock holder,
--                                            -- and every new statement waits behind it.

-- 1. Who is waiting, on what, and behind whom. During a stuck migration this
--    shows one row blocked by the long-running query and many rows blocked by
--    the ALTER.
SELECT a.pid, a.usename, a.application_name, a.client_addr, a.state,
       date_trunc('second', now() - a.query_start) AS waiting,
       a.wait_event_type, a.wait_event,
       pg_blocking_pids(a.pid) AS blocked_by,
       left(a.query, 80) AS query
FROM pg_stat_activity a
WHERE cardinality(pg_blocking_pids(a.pid)) > 0
ORDER BY a.query_start;
-- The root blocker is the pid that appears in blocked_by and is itself not blocked.

-- 2. The lock requests themselves, granted and not, for one table.
SELECT l.pid, l.mode, l.granted, a.state,
       date_trunc('second', now() - a.xact_start) AS xact_age,
       left(a.query, 60) AS query
FROM pg_locks l
JOIN pg_stat_activity a USING (pid)
WHERE l.relation = 'orders'::regclass
ORDER BY l.granted DESC, a.xact_start;

-- 3. The migration, written the way a tool should run it. lock_timeout makes the
--    ALTER give up instead of queueing every other session behind it; the tool
--    retries until it acquires the lock. SQLSTATE 55P03 is the retry signal.
-- SET lock_timeout = '2s';                       -- or: ALTER ROLE migrator SET lock_timeout = '2s'
-- ALTER TABLE orders ADD COLUMN note text;
-- ALTER TABLE orders ADD COLUMN created_by text DEFAULT 'system';     -- no rewrite since PG 11 for a non-volatile default
--
--    retry loop around the file, from a shell:
--      until psql -v ON_ERROR_STOP=1 -f 0042_add_note.sql; do sleep 5; done
--    Rails: disable_ddl_transaction! and algorithm: :concurrently; Alembic: op.get_context().autocommit_block()

-- 4. Indexes and constraints without the long exclusive lock.
-- RESET lock_timeout;             -- CIC waits on old transactions; a 2 s timeout aborts it and leaves an INVALID index
-- CREATE INDEX CONCURRENTLY orders_customer_idx ON orders (customer_id);   -- cannot run inside a transaction block
-- SET lock_timeout = '2s';
-- ALTER TABLE orders ADD CONSTRAINT orders_customer_fk
--   FOREIGN KEY (customer_id) REFERENCES customers NOT VALID;          -- SHARE ROW EXCLUSIVE on both tables, no scan
-- ALTER TABLE orders VALIDATE CONSTRAINT orders_customer_fk;           -- scans under SHARE UPDATE EXCLUSIVE
-- ALTER TABLE orders ADD CONSTRAINT orders_amount_positive CHECK (amount > 0) NOT VALID;   -- ACCESS EXCLUSIVE, no scan
-- ALTER TABLE orders VALIDATE CONSTRAINT orders_amount_positive;

-- 5. Changing a column type usually rewrites the table (not for binary-coercible
--    changes such as widening varchar(n) or varchar to text). Do it in steps:
--    add the new column, backfill in batches, swap names, drop the old one.

-- 6. Keep the record. log_statement = 'ddl' is cheap and gives you who, what, when;
--    log_lock_waits = on logs every wait longer than deadlock_timeout (1 s).
-- ALTER ROLE migrator SET log_statement = 'ddl';          -- per role; superuser, or PG 15+: GRANT SET ON PARAMETER log_statement TO migrator
-- ALTER DATABASE app SET log_lock_waits = on;             -- per database, same privilege rule
-- (ALTER SYSTEM ... ; SELECT pg_reload_conf(); is the server-wide form)
--
-- 6b. Verify: rehearse in staging with a long SELECT held on orders in one session
--    and the migration in another; query 1 should show the ALTER giving up after 2 s
--    (55P03 in the log) and the retry succeeding; during the real run query 1 returns 0 rows.

