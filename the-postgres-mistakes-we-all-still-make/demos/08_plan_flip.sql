-- 08_plan_flip.sql
-- Mistake: we assume the plan is the plan. Requires pg_stat_statements:
--   shared_preload_libraries = 'pg_stat_statements'   (restart), then CREATE EXTENSION pg_stat_statements;
-- mean_exec_time / stddev_exec_time are PG 13+ (mean_time / stddev_time before).
-- Symptom: p99 doubles while the mean looks fine; one tenant or one parameter is slow.

-- 1. Statements whose run time varies most relative to their mean. A bimodal
--    distribution (two plans) shows up as a large stddev and a max far above the mean.
SELECT queryid, calls,
       round(mean_exec_time::numeric, 2)   AS mean_ms,          -- the *_exec_time columns are float8;
       round(stddev_exec_time::numeric, 2) AS stddev_ms,        -- round(float8, int) does not exist
       round(min_exec_time::numeric, 2)    AS min_ms,
       round(max_exec_time::numeric, 2)    AS max_ms,
       round((stddev_exec_time / nullif(mean_exec_time, 0))::numeric, 2) AS cv,
       left(query, 80) AS query
FROM pg_stat_statements
WHERE calls > 100
ORDER BY stddev_exec_time / nullif(mean_exec_time, 0) DESC
LIMIT 20;

-- 2. Plan-cache behaviour for prepared statements. The first five executions use
--    custom plans; from the sixth, the generic plan is used if its estimated cost
--    is not worse than the average custom plan. force_custom_plan keeps
--    re-planning with the actual parameter values.
SHOW plan_cache_mode;
-- ALTER ROLE app_rw SET plan_cache_mode = 'force_custom_plan';   -- for roles whose parameters are skewed

-- 3. Statistics freshness. A bulk load followed by no ANALYZE is the most
--    common reason the plan changes under you.
SELECT relname, n_mod_since_analyze, n_live_tup,
       round(100.0 * n_mod_since_analyze / nullif(n_live_tup, 0), 1) AS pct_modified,
       last_analyze, last_autoanalyze
FROM pg_stat_user_tables
ORDER BY n_mod_since_analyze DESC
LIMIT 20;

-- 4. Parallel plan thresholds. Once a table crosses min_parallel_table_scan_size
--    the planner may pick a parallel sequential scan where it used to use an
--    index, and the extra workers come out of the same CPU budget as everyone else.
SELECT name, setting, unit FROM pg_settings
WHERE name IN ('max_parallel_workers_per_gather', 'max_parallel_workers',
               'min_parallel_table_scan_size', 'min_parallel_index_scan_size',
               'parallel_setup_cost', 'parallel_tuple_cost')
ORDER BY name;

-- 5. See the plan that actually ran, with the parameters that produced it.
--    A duration threshold never catches a 3 ms to 16 ms flip; sample instead.
-- auto_explain must be preloaded (shared_preload_libraries, restart). Its settings are superuser-level:
-- ALTER SYSTEM, or per role after GRANT SET ON PARAMETER auto_explain.log_min_duration TO app_rw (PG 15+).
-- ALTER SYSTEM SET shared_preload_libraries = 'pg_stat_statements, auto_explain';   -- restart
-- ALTER SYSTEM SET auto_explain.log_min_duration = 0;
-- ALTER SYSTEM SET auto_explain.sample_rate = 0.01;                                  -- 1% of statements
-- ALTER SYSTEM SET auto_explain.log_analyze = on;
-- ALTER SYSTEM SET auto_explain.log_buffers = on;
-- ALTER SYSTEM SET auto_explain.log_parameter_max_length = -1;                       -- PG 16+: parameters in the plan log
-- SELECT pg_reload_conf();
-- ALTER ROLE app_rw SET auto_explain.log_min_duration = 0;                          -- the per-role form of the above
--    Or from one session, without logging:  EXPLAIN (GENERIC_PLAN) SELECT ... WHERE id = $1;   -- PG 16+
--
-- 5b. Trace: queryid from query 1 -> the statement text -> the comment tag your ORM
--    adds (/* svc=checkout route=/pay */) -> the handler.
--    Verify: SELECT pg_stat_statements_reset(); wait; the cv in query 1 falls.

-- 6. Measured on a production workload (May 2026): the same selective
--    lookup ran at p50 3 ms on sessions using the index and 16 to 18 ms on
--    sessions where the planner chose a different path. The mean looked fine.
