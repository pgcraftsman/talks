-- 06_timeouts.sql
-- Mistake: we run without timeouts. Every one of these defaults to 0, meaning unlimited.

-- 1. Current values and where they come from. These are THIS session's values;
--    an administrator's session says nothing about what the application role gets.
SELECT name, setting, unit, source
FROM pg_settings
WHERE name IN ('statement_timeout', 'lock_timeout', 'idle_in_transaction_session_timeout',
               'transaction_timeout',        -- PG 17+
               'idle_session_timeout')       -- PG 14+
ORDER BY name;

-- 2. Per-role and per-database overrides already in place.
SELECT coalesce(r.rolname, '(all roles)') AS role,
       coalesce(d.datname, '(all databases)') AS database,
       s.setconfig
FROM pg_db_role_setting s
LEFT JOIN pg_roles r ON r.oid = s.setrole
LEFT JOIN pg_database d ON d.oid = s.setdatabase
ORDER BY 1, 2;

-- 2b. Login roles with no statement_timeout of their own (the ones to fix first).
SELECT r.rolname
FROM pg_roles r
WHERE r.rolcanlogin AND NOT r.rolsuper AND r.rolname NOT LIKE 'pg\_%'
  AND NOT EXISTS (SELECT 1 FROM pg_db_role_setting s
                  WHERE s.setrole = r.oid AND s.setconfig::text LIKE '%statement_timeout%')
ORDER BY 1;

-- 2c. The symptom, if you have it right now: the longest-running statements.
SELECT pid, usename, application_name, date_trunc('second', now() - query_start) AS running, left(query, 60)
FROM pg_stat_activity
WHERE state = 'active' AND pid <> pg_backend_pid()
ORDER BY query_start
LIMIT 5;

-- 3. Set them per role. Each kind of client gets the limit that fits it.
--    Behind a transaction-mode pooler, role-level settings still apply (they are
--    applied at backend start); session-level SET does not survive the pool.
-- ALTER ROLE app_rw    SET statement_timeout = '30s';
-- ALTER ROLE app_rw    SET lock_timeout = '3s';
-- ALTER ROLE app_rw    SET idle_in_transaction_session_timeout = '30s';
-- ALTER ROLE app_rw    SET transaction_timeout = '5min';          -- PG 17+
-- ALTER ROLE reporting SET statement_timeout = '15min';
-- ALTER ROLE reporting SET idle_in_transaction_session_timeout = '2min';
-- ALTER ROLE migrator  SET lock_timeout = '2s';
-- ALTER ROLE migrator  SET statement_timeout = 0;                 -- long backfills are expected here

-- 4. What a timeout looks like when it fires, so the application can tell them apart:
--    statement_timeout                     SQLSTATE 57014  canceling statement due to statement timeout
--    lock_timeout                          SQLSTATE 55P03  canceling statement due to lock timeout
--    idle_in_transaction_session_timeout   SQLSTATE 25P03  terminating connection due to idle-in-transaction timeout
--    transaction_timeout                   SQLSTATE 25P04  terminating connection due to transaction timeout
--    The last two end the session; the application must reconnect.

-- 4b. Verify: rerun 2b (expect no rows for application roles) and watch the log for
--    57014 / 55P03 / 25P03 / 25P04; the application should handle each of them.
--
