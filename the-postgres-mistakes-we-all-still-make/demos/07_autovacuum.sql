-- 07_autovacuum.sql
-- Mistake: we leave autovacuum at its defaults on large tables.
-- Autovacuum triggers at autovacuum_vacuum_threshold + autovacuum_vacuum_scale_factor * reltuples.
-- Defaults 50 and 0.2: a billion-row table waits for 200 million dead tuples.
-- PG 18+ caps that at autovacuum_vacuum_max_threshold (default 100,000,000).
-- Symptom: a table several times the size of its live data, slow scans, disk full.

-- 1. For each table: dead tuples now, the number that triggers autovacuum, and
--    how far along it is. Honours per-table reloptions.
WITH opts AS (
  SELECT c.oid,
         coalesce((SELECT option_value::float FROM pg_options_to_table(c.reloptions)
                   WHERE option_name = 'autovacuum_vacuum_scale_factor'),
                  current_setting('autovacuum_vacuum_scale_factor')::float) AS scale,
         coalesce((SELECT option_value::int FROM pg_options_to_table(c.reloptions)
                   WHERE option_name = 'autovacuum_vacuum_threshold'),
                  current_setting('autovacuum_vacuum_threshold')::int) AS threshold
  FROM pg_class c WHERE c.relkind IN ('r', 'm'))
SELECT s.schemaname, s.relname, c.reltuples::bigint AS reltuples, s.n_dead_tup,
       round(o.threshold + o.scale * c.reltuples) AS triggers_at,            -- autovacuum uses pg_class.reltuples
       round((100.0 * s.n_dead_tup / nullif(o.threshold + o.scale * c.reltuples, 0))::numeric, 1) AS pct_of_trigger,
       o.scale, s.autovacuum_count, s.last_autovacuum
FROM pg_stat_user_tables s JOIN pg_class c ON c.oid = s.relid JOIN opts o ON o.oid = s.relid
WHERE c.reltuples > 1000000
ORDER BY s.n_dead_tup DESC
LIMIT 20;

-- 2. Large tables still on the global defaults.
SELECT c.oid::regclass AS table, c.reltuples::bigint AS rows, pg_size_pretty(pg_total_relation_size(c.oid)) AS size
FROM pg_class c
WHERE c.relkind = 'r' AND c.reltuples > 10000000
  AND NOT EXISTS (SELECT 1 FROM pg_options_to_table(c.reloptions) WHERE option_name LIKE 'autovacuum%')
ORDER BY c.reltuples DESC;

-- 3. What autovacuum is doing right now.
SELECT a.pid, p.relid::regclass AS table, p.phase,
       p.heap_blks_scanned, p.heap_blks_total,
       round(100.0 * p.heap_blks_scanned / nullif(p.heap_blks_total, 0), 1) AS pct_scanned,
       p.index_vacuum_count, p.num_dead_item_ids,          -- PG 17+ (num_dead_tuples before)
       date_trunc('second', now() - a.xact_start) AS running_for,
       a.query
FROM pg_stat_progress_vacuum p JOIN pg_stat_activity a USING (pid);

-- 4. The throttle. cost_limit / cost_delay is the budget per second, SHARED by all
--    running autovacuum workers (tables with their own cost settings are exempt
--    from the balancing); a dirtied page costs vacuum_cost_page_dirty (20), a
--    miss 2, a hit 1. autovacuum_vacuum_cost_limit = -1 means "use vacuum_cost_limit".
SELECT name, setting, unit FROM pg_settings
WHERE name IN ('autovacuum_vacuum_cost_limit', 'autovacuum_vacuum_cost_delay', 'vacuum_cost_limit',
               'vacuum_cost_page_hit', 'vacuum_cost_page_miss', 'vacuum_cost_page_dirty',
               'autovacuum_max_workers', 'autovacuum_naptime', 'maintenance_work_mem',
               'autovacuum_work_mem')
ORDER BY name;

-- 5. Per-table settings for anything large and busy.
-- ALTER TABLE events SET (autovacuum_vacuum_scale_factor   = 0.01,
--                         autovacuum_vacuum_threshold      = 10000,
--                         autovacuum_analyze_scale_factor  = 0.005,
--                         autovacuum_vacuum_cost_delay     = 0);     -- let this table's worker run unthrottled

-- 5b. Verify: after the ALTER TABLE, query 1 shows pct_of_trigger near 100 then
--    falling, last_autovacuum advances, n_dead_tup drops, query 3 shows the worker.
--    Trace the writer: pg_stat_user_tables ORDER BY n_tup_upd + n_tup_del, then
--    pg_stat_statements for the statement.
--
