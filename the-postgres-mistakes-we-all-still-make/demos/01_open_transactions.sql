-- 01_open_transactions.sql
-- Mistake: we still leave transactions open (idle in transaction) and we still run
-- long ones and call them 'just a read'. Same damage, two doors in: the xmin horizon.
-- Part A is the idle-in-transaction case, Part B is everything else that pins the horizon.

----------------------------------------------------------------------------- Part A
-- Mistake: we still leave transactions open while we go do something else.
--
-- What it looks like in the app (Python/psycopg, autocommit off, the default):
--
--   cur.execute("SELECT * FROM orders WHERE id = %s FOR UPDATE", (oid,))
--   charge = payments_api.charge(card, amount)      # 2-30 s over the network
--   cur.execute("UPDATE orders SET status = 'paid' WHERE id = %s", (oid,))
--   conn.commit()
--
-- Between the SELECT and the UPDATE the session is 'idle in transaction'. It
-- holds its row locks and, because FOR UPDATE assigned it a transaction id, it
-- pins the xmin horizon: vacuum cannot remove anything newer than that xid on ANY
-- table in the database. In the default READ COMMITTED it holds no snapshot
-- between statements (backend_xmin is NULL); in REPEATABLE READ it holds both.

-- 1. Who is idle in transaction right now, and for how long?
SELECT pid, usename, application_name, client_addr, state,
       date_trunc('second', now() - xact_start)   AS xact_age,
       date_trunc('second', now() - state_change) AS idle_for,
       backend_xid, backend_xmin,
       greatest(age(backend_xid), age(backend_xmin)) AS horizon_age,
       left(query, 80)                            AS last_statement
FROM pg_stat_activity
WHERE state LIKE 'idle in transaction%'
ORDER BY xact_start;

-- 2. What are they holding? (row locks show as the table's RowExclusive/
--    RowShare lock plus 'transactionid' locks other sessions wait on)
SELECT a.pid, a.state, l.locktype, l.relation::regclass AS relation, l.mode, l.granted
FROM pg_locks l
JOIN pg_stat_activity a USING (pid)
WHERE a.state LIKE 'idle in transaction%'
ORDER BY a.pid, l.relation;

-- 3. Who is stuck behind them?
SELECT w.pid AS waiting_pid, w.wait_event_type, w.wait_event,
       date_trunc('second', now() - w.query_start) AS waiting_for,
       pg_blocking_pids(w.pid) AS blocked_by, left(w.query, 70) AS waiting_query
FROM pg_stat_activity w
WHERE cardinality(pg_blocking_pids(w.pid)) > 0
ORDER BY w.query_start;

-- 4. The fix, server side. Set the timeout above the longest legitimate external
--    call, or give that call its own shorter timeout. A session ended by the
--    timeout gets SQLSTATE 25P03 and must reconnect. Set it on the role, not server-wide, so the
--    reporting user and the migration user can have different limits.
--    (Run these; they are the actual fix, not a demo.)
-- ALTER ROLE app_rw SET idle_in_transaction_session_timeout = '30s';
-- ALTER ROLE app_rw SET transaction_timeout = '5min';     -- PG 17+: caps the whole txn, idle or not

-- 5. The fix, app side: do not open the transaction until the network call is done.
--
--      charge = payments.charge(card, amount, idempotency_key=oid)   # no transaction open
--      with conn.transaction():
--          cur.execute("UPDATE orders SET status = 'paid' WHERE id = %s AND status = 'pending'", (oid,))
--      # on SQLSTATE 25P03: reconnect and retry the UPDATE, never the charge
--
--    The conditional UPDATE replaces the FOR UPDATE guard; the idempotency key
--    keeps a retry from charging twice.
--
-- 5b. Verify: rerun Part A query 1 at peak; expect nothing older than the timeout,
--    and FATAL 25P03 lines in the log grouped by application_name.

----------------------------------------------------------------------------- Part B
-- Mistake: we still run long transactions and assume "it's only a read".
--
-- Any transaction with a snapshot pins the xmin horizon. Dead tuples newer than
-- the oldest snapshot are not removable, on any table, no matter how many times
-- autovacuum runs. The chart charts/vacuum-holdback.svg is this exact run:
-- 3 autovacuum passes while the session was open (7 in the whole run), dead tuples
-- near 45%, zero reclaimed, until the session hit idle_in_transaction_session_timeout.

-- 1. The four places a horizon can be pinned, in one list, oldest first.
--    backend_xid (an open transaction) and backend_xmin (a snapshot) both count.
--    A physical slot's xmin comes from a standby's hot_standby_feedback and pins
--    every table; a logical slot's catalog_xmin pins catalog tuples and retains WAL.
SELECT 'backend'          AS holder, pid::text AS who,
       greatest(age(backend_xid), age(backend_xmin)) AS xmin_age,
       date_trunc('second', now() - xact_start) AS held_for, state AS detail,
       coalesce(nullif(application_name, ''), usename) || ': ' || left(query, 50) AS extra
FROM pg_stat_activity
WHERE (backend_xid IS NOT NULL OR backend_xmin IS NOT NULL)
  AND backend_type = 'client backend' AND pid <> pg_backend_pid()
UNION ALL
SELECT CASE WHEN plugin IS NULL THEN 'physical slot (xmin)' ELSE 'logical slot (catalog_xmin)' END,
       slot_name, greatest(age(xmin), age(catalog_xmin)), NULL,
       CASE WHEN active THEN 'active' ELSE 'INACTIVE' END, coalesce(plugin, 'physical')
FROM pg_replication_slots
WHERE xmin IS NOT NULL OR catalog_xmin IS NOT NULL
UNION ALL
SELECT 'standby (hot_standby_feedback)', application_name, age(backend_xmin), NULL, state, client_addr::text
FROM pg_stat_replication
WHERE backend_xmin IS NOT NULL
UNION ALL
SELECT 'prepared transaction', gid, age(transaction), date_trunc('second', now() - prepared), 'prepared', owner
FROM pg_prepared_xacts
ORDER BY xmin_age DESC NULLS LAST;

-- 2. Proof that vacuum is running but cannot reclaim. VACUUM VERBOSE says it
--    out loud (PG 15+ wording):
--
--    INFO:  vacuuming "app.public.orders"
--    INFO:  finished vacuuming "app.public.orders": index scans: 0
--    tuples: 0 removed, 1483112 remain, 612004 are dead but not yet removable
--    removable cutoff: 982144, which was 61930 XIDs old when operation ended
--
--    "dead but not yet removable" + an old cutoff = somebody is holding a snapshot.
-- VACUUM (VERBOSE) orders;

-- 3. Watch autovacuum spin on it:
SELECT p.pid, p.relid::regclass AS table, p.phase, p.heap_blks_scanned, p.heap_blks_total,
       p.num_dead_item_ids,                       -- PG 17+ (num_dead_tuples before)
       date_trunc('second', now() - a.xact_start) AS running_for
FROM pg_stat_progress_vacuum p JOIN pg_stat_activity a USING (pid);

-- 4. How far behind is the horizon on each table?  n_dead_tup that does not
--    fall after last_autovacuum is the signature.
SELECT schemaname, relname, n_live_tup, n_dead_tup,
       round(100.0 * n_dead_tup / greatest(n_live_tup, 1), 1) AS dead_pct,
       autovacuum_count, last_autovacuum
FROM pg_stat_user_tables
WHERE n_dead_tup > 10000
ORDER BY n_dead_tup DESC
LIMIT 20;

-- 5. Fixes, by holder:
--    backend          -> statement_timeout / transaction_timeout on the role (06_timeouts.sql);
--                        split the batch job into bounded transactions (02_bulk_delete.sql).
--    replication slot -> drop slots nobody consumes: SELECT pg_drop_replication_slot('old_cdc');
--                        cap the damage with max_slot_wal_keep_size; PG 18 adds
--                        idle_replication_slot_timeout to invalidate idle slots for you.
--    standby          -> hot_standby_feedback = on trades primary bloat for fewer
--                        query cancels on the replica. Know which side you chose.
--    prepared xact    -> ROLLBACK PREPARED 'gid'; and ask why XA is on at all
--                        (max_prepared_transactions > 0).

