-- 00_bubble_up.sql
-- The thesis of the talk in one query: don't stare at a dashboard, ask the
-- database what is wrong right now and get back a ranked issue list.
-- Read-only. Works on PG 14+ (uses pg_blocking_pids, pg_stat_user_indexes).
--
-- Needs GRANT pg_monitor TO <you> (or pg_read_all_stats). Without it, other roles'
-- sessions show NULL state/query/xact_start and most CTEs return nothing: an
-- all-clear result from an unprivileged role means nothing. Run it once per
-- database; pg_stat_user_* is per database.
-- Every CTE below is one of the mistakes in the talk. Run it on a schedule and
-- page on the critical rows.

WITH
idle_in_tx AS (
  SELECT 'idle in transaction'::text AS issue, 'critical'::text AS sev,
         format('pid %s (%s) has been idle inside a transaction for %s; last statement: %s',
                pid, coalesce(nullif(application_name, ''), usename),
                date_trunc('second', now() - state_change), left(query, 60)) AS detail,
         extract(epoch FROM now() - state_change) AS score
  FROM pg_stat_activity
  WHERE state LIKE 'idle in transaction%'
    AND now() - state_change > interval '30 seconds'),

long_xact AS (
  SELECT 'long-running transaction', 'warning',
         -- backend_xmin is a snapshot, backend_xid an open transaction; either pins the horizon
         format('pid %s (%s) open for %s, pinning the horizon (age %s): %s',
                pid, coalesce(nullif(application_name, ''), usename),
                date_trunc('second', now() - xact_start),
                greatest(age(backend_xmin), age(backend_xid)), left(query, 60)),
         extract(epoch FROM now() - xact_start)
  FROM pg_stat_activity
  WHERE (backend_xmin IS NOT NULL OR backend_xid IS NOT NULL)
    AND backend_type = 'client backend'
    AND now() - xact_start > interval '5 minutes'
    AND pid <> pg_backend_pid()),

xmin_holders AS (
  -- physical slot xmin (from a standby's hot_standby_feedback) pins every table;
  -- a logical slot's catalog_xmin pins catalog tuples only and retains WAL
  SELECT 'replication slot pinning xmin', 'warning',
         format('slot %s (%s) xmin age %s, catalog_xmin age %s%s', slot_name, coalesce(plugin, 'physical'),
                age(xmin), age(catalog_xmin), CASE WHEN active THEN '' ELSE ', INACTIVE' END),
         greatest(age(xmin), age(catalog_xmin))
  FROM pg_replication_slots
  WHERE xmin IS NOT NULL OR catalog_xmin IS NOT NULL
  UNION ALL
  SELECT 'prepared transaction', 'critical',
         format('%s prepared %s ago by %s', gid, date_trunc('second', now() - prepared), owner),
         extract(epoch FROM now() - prepared)
  FROM pg_prepared_xacts),

blocked AS (
  SELECT 'blocked session', 'warning',
         format('pid %s waiting %s on %s/%s, blocked by %s: %s',
                a.pid, date_trunc('second', now() - a.query_start), a.wait_event_type, a.wait_event,
                pg_blocking_pids(a.pid), left(a.query, 60)),
         extract(epoch FROM now() - a.query_start)
  FROM pg_stat_activity a
  WHERE cardinality(pg_blocking_pids(a.pid)) > 0),

bloat AS (
  SELECT 'dead tuples', 'warning',
         format('%s.%s is %s%% dead (%s live / %s dead), last autovacuum %s',
                schemaname, relname, round(100.0 * n_dead_tup / greatest(n_live_tup, 1), 1),
                n_live_tup, n_dead_tup, coalesce(last_autovacuum::text, 'never')),
         100.0 * n_dead_tup / greatest(n_live_tup, 1)
  FROM pg_stat_user_tables
  WHERE n_live_tup > 100000 AND n_dead_tup > 0.2 * n_live_tup),

unused_idx AS (
  SELECT 'unused index', 'info',
         format('%s on %s.%s: %s, 0 scans since %s',
                s.indexrelname, s.schemaname, s.relname,
                pg_size_pretty(pg_relation_size(s.indexrelid)),
                coalesce((SELECT stats_reset::date::text FROM pg_stat_database WHERE datname = current_database()), 'startup')),
         pg_relation_size(s.indexrelid) / 1e6
  FROM pg_stat_user_indexes s JOIN pg_index i USING (indexrelid)
  WHERE s.idx_scan = 0 AND NOT i.indisunique AND NOT i.indisprimary
    AND pg_relation_size(s.indexrelid) > 10 * 1024 * 1024
    AND NOT EXISTS (SELECT 1 FROM pg_constraint c WHERE c.conindid = s.indexrelid)),

invalid_idx AS (
  SELECT 'invalid index', 'warning',
         format('%s on %s is invalid (failed CREATE INDEX CONCURRENTLY?)', indexrelid::regclass, indrelid::regclass),
         1
  FROM pg_index WHERE NOT indisvalid),

conns AS (
  SELECT 'connections', 'critical',
         format('%s of max_connections=%s in use (%s%%)', count(*), current_setting('max_connections'),
                round(100.0 * count(*) / current_setting('max_connections')::int)),
         100.0 * count(*) / current_setting('max_connections')::int
  FROM pg_stat_activity
  WHERE backend_type = 'client backend'
  HAVING count(*) > 0.8 * current_setting('max_connections')::int),

timeouts AS (
  -- pg_settings shows THIS session's values; the roles that matter are the ones that log in
  SELECT 'no statement_timeout on login role', 'info',
         format('role %s has no statement_timeout override', r.rolname), 1
  FROM pg_roles r
  WHERE r.rolcanlogin AND NOT r.rolsuper AND r.rolname NOT LIKE 'pg\_%'
    AND NOT EXISTS (SELECT 1 FROM pg_db_role_setting s
                    WHERE s.setrole = r.oid AND s.setconfig::text LIKE '%statement_timeout%')),

wraparound AS (
  SELECT 'transaction id age', 'critical',
         format('%s: datfrozenxid age %s (shutdown at ~2.1 billion)', datname, age(datfrozenxid)),
         age(datfrozenxid)
  FROM pg_database WHERE age(datfrozenxid) > 1000000000)

SELECT issue, sev, detail
FROM (
  SELECT * FROM idle_in_tx UNION ALL SELECT * FROM long_xact UNION ALL SELECT * FROM xmin_holders
  UNION ALL SELECT * FROM blocked      UNION ALL SELECT * FROM bloat     UNION ALL SELECT * FROM unused_idx
  UNION ALL SELECT * FROM invalid_idx  UNION ALL SELECT * FROM conns     UNION ALL SELECT * FROM timeouts
  UNION ALL SELECT * FROM wraparound
) x(issue, sev, detail, score)
ORDER BY array_position(ARRAY['critical', 'warning', 'info'], sev), score DESC;
