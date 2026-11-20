\set ON_ERROR_STOP on
\pset format unaligned
\pset tuples_only on
DROP TABLE IF EXISTS idxcost;
CREATE TABLE idxcost (id bigint PRIMARY KEY, a int, b int, c int, d int, e int, f int, g int, payload text) WITH (fillfactor = 100);
INSERT INTO idxcost
SELECT i, (random()*1e6)::int, (random()*1e6)::int, (random()*1e6)::int, (random()*1e6)::int,
       (random()*1e6)::int, (random()*1e6)::int, (random()*1e6)::int, repeat('x', 60)
  FROM generate_series(1, 1000000) i;
VACUUM (ANALYZE) idxcost;
CREATE TEMP TABLE results (indexes int, wal_bytes_per_row numeric, heap_bytes bigint, index_bytes bigint, new_index_bytes bigint);
DO $$
DECLARE k int; col text; l0 pg_lsn; l1 pg_lsn; before bigint; after bigint; cols text[] := ARRAY['a','b','c','d','e','f','g'];
BEGIN
  FOR k IN 0..7 LOOP
    IF k > 0 THEN
      col := cols[k];
      before := (SELECT coalesce(sum(pg_relation_size(indexrelid)), 0) FROM pg_index WHERE indrelid = 'idxcost'::regclass);
      EXECUTE format('CREATE INDEX idxcost_%s ON idxcost (%s)', col, col);
      after := (SELECT sum(pg_relation_size(indexrelid)) FROM pg_index WHERE indrelid = 'idxcost'::regclass);
    ELSE
      before := 0; after := (SELECT sum(pg_relation_size(indexrelid)) FROM pg_index WHERE indrelid = 'idxcost'::regclass);
    END IF;
    CHECKPOINT;
    UPDATE idxcost SET a = a + 1 WHERE id BETWEEN 1 AND 10000;      -- warm: full-page images land here
    l0 := pg_current_wal_insert_lsn();
    UPDATE idxcost SET a = a + 1 WHERE id BETWEEN 1 AND 10000;      -- measured: same pages, no FPIs
    l1 := pg_current_wal_insert_lsn();
    INSERT INTO results VALUES (k, round(pg_wal_lsn_diff(l1, l0) / 10000.0, 1), pg_relation_size('idxcost'),
      (SELECT sum(pg_relation_size(indexrelid)) FROM pg_index WHERE indrelid = 'idxcost'::regclass), after - before);
  END LOOP;
END $$;
SELECT indexes || ',' || wal_bytes_per_row || ',' || heap_bytes || ',' || index_bytes || ',' || new_index_bytes FROM results ORDER BY indexes;
