#!/usr/bin/env bash
export PATH="$HOME/pg/17.10/bin:$PATH"
D="-h /tmp -p 1710 storm"
m() { psql -q $D -c CHECKPOINT >/dev/null; pgbench -n -f upd.sql -c 4 -j 4 -T 5 $D >/dev/null 2>&1; psql -q $D -c CHECKPOINT >/dev/null; pgbench -n -f upd.sql -c 4 -j 4 -T 20 $D 2>&1 | grep -E '^tps|latency average' | tr '\n' ' '; echo; }
echo "indexes now: $(psql -At $D -c "select count(*)-1 from pg_index where indrelid='idxcost'::regclass")"
m; m
for c in a b c d e f g; do psql -q $D -c "DROP INDEX IF EXISTS idxcost_$c" >/dev/null; done
echo "0 indexes:"; m; m
for c in a b c d e f g; do psql -q $D -c "CREATE INDEX idxcost_$c ON idxcost ($c)" >/dev/null; done
echo "7 indexes:"; m; m
