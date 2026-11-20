-- 05_connection_storm.sql
-- Mistake: we let connection storms reach the database.
-- Connection churn (how fast sessions open and close) is the early signal;
-- connection count against max_connections is the late one.

-- 1. Server-side session counters (PostgreSQL 14+). Sample this twice a minute
--    apart and subtract: (sessions_2 - sessions_1) / 60 is new connections per second.
SELECT datname, sessions, sessions_abandoned, sessions_fatal, sessions_killed,
       xact_commit, stats_reset
FROM pg_stat_database
WHERE datname = current_database();

-- 2. Connections by state and application. Many idle rows means pools larger
--    than the work; many distinct application_name values means no pooler.
SELECT coalesce(nullif(application_name, ''), '(none)') AS application, state, count(*)
FROM pg_stat_activity
WHERE backend_type = 'client backend'
GROUP BY 1, 2
ORDER BY 3 DESC;

-- 3. How close to the ceiling, and how much of it is reserved.
SELECT count(*) AS client_backends,
       current_setting('max_connections')::int AS max_connections,
       current_setting('superuser_reserved_connections')::int AS superuser_reserved,
       current_setting('reserved_connections')::int AS reserved,                 -- PG 16+
       round(100.0 * count(*) / current_setting('max_connections')::int, 1) AS pct_used
FROM pg_stat_activity
WHERE backend_type = 'client backend';

-- 4. Age distribution of connections. A storm shows up as many connections
--    younger than a few seconds; a healthy pool shows connections hours old.
SELECT CASE WHEN now() - backend_start < interval '10 seconds' THEN '< 10 s'
            WHEN now() - backend_start < interval '1 minute'   THEN '< 1 min'
            WHEN now() - backend_start < interval '1 hour'     THEN '< 1 hour'
            ELSE '>= 1 hour' END AS connection_age,
       count(*)
FROM pg_stat_activity
WHERE backend_type = 'client backend'
GROUP BY 1
ORDER BY min(now() - backend_start);

-- 4b. sessions_fatal counts sessions that ended on a FATAL error. A connection
--    refused at max_connections never became a session, so it is not counted
--    anywhere in pg_stat_database; it shows only in the server log:
--      FATAL:  sorry, too many clients already
--
-- 5. The fix is outside the database.
--    pgbouncer, transaction mode, server side sized to the database:
--
--      [pgbouncer]
--      pool_mode = transaction
--      default_pool_size = 20            ; toward Postgres, per database/user pair
--      max_client_conn = 5000            ; from the application
--      server_idle_timeout = 60
--      max_prepared_statements = 100     ; pgbouncer 1.21+; psycopg3 auto-prepares after 5 executions
--
--    transaction mode breaks session state: SET (use SET LOCAL), advisory locks,
--    LISTEN/NOTIFY, and server-side prepared statements on older pgbouncer
--    (psycopg: conn.prepare_threshold = None if you cannot upgrade).
--
--    In the client: one pool per process sized to the database's cores, not the
--    application's thread count; connect_timeout in the DSN; backoff with jitter:
--
--      pool = ConnectionPool(DSN, min_size=2, max_size=10, timeout=5)      # psycopg_pool
--      delay = min(30, 0.1 * 2 ** attempt) * random.uniform(0.5, 1.5)      # between reconnects
--
-- 5b. Verify: query 4 shows connections older than an hour and few under 10 s;
--    the sessions delta from query 1 is near zero; the log stops showing
--    "too many clients".

