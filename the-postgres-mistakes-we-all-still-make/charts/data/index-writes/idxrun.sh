#!/usr/bin/env bash
set -u
export PATH="$HOME/pg/17.10/bin:$PATH"
D="-h /tmp -p 1710 storm"
OUT=/tmp/pgday-storm/idxout; mkdir -p $OUT
echo "indexes,tps,latency_ms,wal_mb,wal_bytes_per_update"
for k in 7 6 5 4 3 2 1 0; do
  if [ $k -lt 7 ]; then
    col=$(echo g f e d c b a | cut -d' ' -f$((7-k))); psql -q $D -c "DROP INDEX idxcost_$col" >/dev/null
  fi
  psql -q $D -c "CHECKPOINT" >/dev/null
  pgbench -n -f upd.sql -c 20 -j 10 -T 5 $D >/dev/null 2>&1    # warm
  psql -q $D -c "CHECKPOINT" >/dev/null
  l0=$(psql -At $D -c "select pg_current_wal_insert_lsn()")
  pgbench -n -f upd.sql -c 20 -j 10 -T 15 $D > $OUT/k$k.txt 2>&1
  l1=$(psql -At $D -c "select pg_current_wal_insert_lsn()")
  wal=$(psql -At $D -c "select pg_wal_lsn_diff('$l1','$l0')")
  tps=$(grep -E '^tps' $OUT/k$k.txt | sed -E 's/.*= ([0-9.]+).*/\1/'); lat=$(grep 'latency average' $OUT/k$k.txt | sed -E 's/.*= ([0-9.]+) ms/\1/')
  n=$(grep 'number of transactions actually processed' $OUT/k$k.txt | sed -E 's/.*: ([0-9]+).*/\1/')
  echo "$k,$tps,$lat,$(echo "scale=1; $wal/1000000" | bc),$(echo "$wal/$n" | bc)"
done
