#!/usr/bin/env bash
set -u
export PATH="$HOME/pg/17.10/bin:$PATH"
OUT=/tmp/pgday-storm/out2; mkdir -p "$OUT"; rm -f "$OUT"/*.txt
C=20; J=10; T=15; RT=12
DIRECT="-h /tmp -p 1710"
POOLED="-h /tmp/pgday-storm -p 6432"
run() { local name=$1; shift; local path=$1; shift
  echo "== $name"
  pgbench -S -n -c $C -j $J $path "$@" storm > "$OUT/$name.txt" 2>&1
  grep -E '^tps|latency average|average connection time|schedule lag|error' "$OUT/$name.txt" | head -6; }
run persistent_direct "$DIRECT" -T $T
run persistent_pooled "$POOLED" -T $T
run churn_direct "$DIRECT" -C -T $T
run churn_pooled "$POOLED" -C -T $T
for R in 100 200 400 800 1600; do
  run "rate${R}_direct" "$DIRECT" -C -R $R -T $RT
  run "rate${R}_pooled" "$POOLED" -C -R $R -T $RT
done
echo DONE
