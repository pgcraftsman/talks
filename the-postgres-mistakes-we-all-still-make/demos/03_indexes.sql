-- 03_indexes.sql
-- Mistake: we build indexes nobody reads, and we index columns that change often.
-- Read-only except the commented-out fixes. PostgreSQL 16+ for last_idx_scan and
-- n_tup_newpage_upd; everything else works on 12+.

-- 1. Indexes with zero scans since the last stats reset, largest first.
--    Excludes unique and primary key indexes and anything backing a constraint.
SELECT s.schemaname, s.relname AS table, s.indexrelname AS index,
       pg_size_pretty(pg_relation_size(s.indexrelid)) AS size,
       s.idx_scan, s.last_idx_scan,
       (SELECT stats_reset FROM pg_stat_database WHERE datname = current_database()) AS stats_window_start
FROM pg_stat_user_indexes s
JOIN pg_index i USING (indexrelid)
WHERE s.idx_scan = 0
  AND NOT i.indisunique AND NOT i.indisprimary
  AND NOT EXISTS (SELECT 1 FROM pg_constraint c WHERE c.conindid = s.indexrelid)
ORDER BY pg_relation_size(s.indexrelid) DESC;

-- 2. Exact duplicates: same columns, operator classes, expression and predicate.
SELECT indrelid::regclass AS table,
       array_agg(indexrelid::regclass ORDER BY indexrelid) AS duplicates,
       pg_size_pretty(sum(pg_relation_size(indexrelid))) AS total_size
FROM pg_index
GROUP BY indrelid, indkey::text, indclass::text, coalesce(indexprs::text, ''), coalesce(indpred::text, '')
HAVING count(*) > 1;

-- 3. Invalid indexes left behind by a failed CREATE INDEX CONCURRENTLY.
--    They are maintained on every write and never used by the planner.
SELECT i.indexrelid::regclass AS index, i.indrelid::regclass AS table,
       pg_size_pretty(pg_relation_size(i.indexrelid)) AS size, i.indisvalid, i.indisready
FROM pg_index i
WHERE NOT i.indisvalid OR NOT i.indisready;

-- 4. HOT ratio. A low hot_pct on a busy table means an indexed column is being
--    updated, or the page has no room (fillfactor). The counters are cumulative
--    since stats reset, so a recent regression only shows in a delta: sample twice.
--    n_tup_upd - n_tup_hot_upd - n_tup_newpage_upd = non-HOT updates that stayed
--    on their page, which is the indexed-column case. n_tup_newpage_upd is PG 16+.
SELECT relname, n_tup_upd, n_tup_hot_upd,
       round(100.0 * n_tup_hot_upd / nullif(n_tup_upd, 0), 1) AS hot_pct,
       n_tup_newpage_upd,
       n_dead_tup
FROM pg_stat_user_tables
WHERE n_tup_upd > 0
ORDER BY n_tup_upd DESC
LIMIT 20;

-- 5. Which indexes cover a column that is updated often? Join the hot table from
--    step 4 against pg_index to see which index is disqualifying HOT.
--    (Replace 'pgbench_accounts' and 'abalance'.)
SELECT i.indexrelid::regclass AS index, pg_get_indexdef(i.indexrelid) AS definition
FROM pg_index i
JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY (i.indkey)
WHERE i.indrelid = 'pgbench_accounts'::regclass AND a.attname = 'abalance';

-- 6. Before dropping anything:
--    - check stats_reset above: a recent reset means the zero is meaningless
--    - run step 1 on every replica; each node counts its own scans
--    - find who wanted it:  git log -S 'ix_pgbench_accounts_abalance' -- db/migrations
--    - find queries that might use it:
--        SELECT queryid, calls, left(query, 80) FROM pg_stat_statements WHERE query ILIKE '%abalance%';
--    - keep the definition so recreating is one statement
--    - if the column must stay indexed, give HOT room instead: ALTER TABLE t SET (fillfactor = 85)
-- SELECT pg_get_indexdef('ix_pgbench_accounts_abalance'::regclass);
-- DROP INDEX CONCURRENTLY ix_pgbench_accounts_abalance;   -- plain DROP INDEX takes ACCESS EXCLUSIVE on the table

-- 7. Verify: after DROP INDEX CONCURRENTLY, step 1 no longer lists it, total index
--    size falls, and hot_pct on the table rises on the next sample.
--
