"""Extract chart series from the May 2026 workload run logs into small CSVs.
Run with: python3 -I extract_series.py <workloads_dir> <out_dir>
"""
import re, sys, csv, datetime as dt, pathlib
W, OUT = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
TS = "%Y-%m-%d %H:%M:%S,%f"
def ts(line): return dt.datetime.strptime(line[:23], TS)

# 1) vacuum-holdback: dead%, autovac count, holdback tx_age, from snapshot lines
snap = re.compile(r"rate=([\d.]+)/s target=([\d.]+)/s live=(\d+) dead=(\d+) \(([\d.]+)%\) size=([\d.]+)MB autovac=(\d+)(?:.*?\| holdback: pid=(\d+) xmin=(\S+) tx_age=(\d+)s)?")
for name in ["vacuum-holdback", "vacuum-holdback-60min"]:
    rows, t0 = [], None
    for line in open(W/"logs"/f"{name}.log", errors="replace"):
        m = snap.search(line.strip())
        if not m: continue
        t = ts(line); t0 = t0 or t
        rows.append(dict(elapsed_s=round((t-t0).total_seconds(),1), rate=m[1], dead_pct=m[5], size_mb=m[6],
                         autovac=m[7], holdback_pid=m[8] or "", tx_age_s=m[10] or ""))
    with open(OUT/f"{name}.csv","w",newline="") as f:
        w=csv.DictWriter(f, fieldnames=rows[0].keys()); w.writeheader(); w.writerows(rows)
    print(name, len(rows), "rows; last:", rows[-1])
    # kill events
    for line in open(W/"logs"/f"{name}.log", errors="replace"):
        if "idle-in-transaction" in line or "terminat" in line.lower():
            print("  EVENT:", line.strip()[:160]); 

# 2) high-bloat: dead% vs cumulative updates, no-index (60min) vs with-index (postindex)
snap2 = re.compile(r"rate=([\d.]+)/s target=([\d.]+)/s live=(\d+) dead=(\d+) \(([\d.]+)%\) size=([\d.]+)MB autovac_count=(\d+)")
for name, label in [("high-bloat-60min","no_index"),("high-bloat-postindex","with_index")]:
    rows, t0, prev_t, cum = [], None, None, 0.0
    for line in open(W/"logs"/f"{name}.log", errors="replace"):
        m = snap2.search(line)
        if not m: continue
        t = ts(line); t0 = t0 or t
        if prev_t: cum += float(m[1]) * (t-prev_t).total_seconds()
        prev_t = t
        rows.append(dict(elapsed_s=round((t-t0).total_seconds(),1), rate=m[1], cum_updates=int(cum), dead=m[4], dead_pct=m[5], size_mb=m[6]))
    with open(OUT/f"high-bloat-{label}.csv","w",newline="") as f:
        w=csv.DictWriter(f, fieldnames=rows[0].keys()); w.writeheader(); w.writerows(rows)
    print(name, len(rows), "rows; first:", rows[0], "last:", rows[-1])

# 3) connection-churn tuned: actual vs target conn/s, plus rejection counts per 5s window
rate = re.compile(r"rate: actual=([\d.]+)/s target=([\d.]+)/s")
for name in ["connection-churn-tuned", "connection-churn"]:
    rows, t0, rej = [], None, 0
    for line in open(W/"logs"/f"{name}.log", errors="replace"):
        if "Too many connections attempts" in line or "rate limit exceeded" in line: rej += 1
        m = rate.search(line)
        if not m: continue
        t = ts(line); t0 = t0 or t
        rows.append(dict(elapsed_s=round((t-t0).total_seconds(),1), actual=m[1], target=m[2], rejections_cum=rej))
    with open(OUT/f"{name}.csv","w",newline="") as f:
        w=csv.DictWriter(f, fieldnames=rows[0].keys()); w.writeheader(); w.writerows(rows)
    print(name, len(rows), "rows; last:", rows[-1])
