-- 02_bulk_delete.sql
-- Mistake: we still bulk DELETE instead of partitioning.
--
-- The nightly job:
--
--   DELETE FROM events WHERE created_at < now() - interval '90 days';
--
-- On a 2 billion row table that is one transaction (see 01_open_transactions.sql),
-- one dead tuple per row and one heap WAL record per row, replayed on every
-- replica. The indexes are not touched by the DELETE; vacuum pays for them
-- afterwards, scanning every index in full to remove the dead entries, and
-- the pages it empties are reused, not returned.

-- 1. After the fact: which statement wrote last night's WAL spike?
--    (pg_stat_statements; wal_bytes needs PG 13+)
SELECT left(query, 60) AS query, calls, rows,
       pg_size_pretty(wal_bytes::bigint) AS wal,
       round(total_exec_time::numeric / 1000) AS seconds
FROM pg_stat_statements
ORDER BY wal_bytes DESC
LIMIT 5;

-- 2. Dead rows by table:
SELECT relname, n_tup_del, n_dead_tup, n_live_tup,
       round(100.0 * n_dead_tup / greatest(n_live_tup, 1), 1) AS dead_pct,
       pg_size_pretty(pg_table_size(relid))   AS heap,
       pg_size_pretty(pg_indexes_size(relid)) AS indexes,
       last_autovacuum
FROM pg_stat_user_tables
WHERE relname = 'events';