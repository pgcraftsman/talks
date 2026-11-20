"""Render the talk's data charts as SVG+PNG from charts/data/*.csv.
Run: ../.venv/bin/python make_charts.py
Dark surface; palette and chrome follow the dataviz reference palette. The in-chart
title is the slide heading (slides embed charts with no markdown heading), so each
title states what the chart shows, with the real numbers.
"""
import csv, pathlib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

HERE = pathlib.Path(__file__).parent
D = HERE / "data"
SURF, INK, INK2, MUTED, GRID, AXIS = "#1a1a19", "#f0efec", "#c3c2b7", "#898781", "#2c2c2a", "#383835"
S1, S2, S3 = "#3987e5", "#d95926", "#199e70"   # categorical slots 1-3 (dark steps)
FS_TICK, FS_LABEL, FS_ANN, FS_TITLE, FS_FOOT = 13, 13, 13.5, 17, 11

plt.rcParams.update({
    "font.family": "sans-serif", "font.sans-serif": ["DejaVu Sans", "Segoe UI", "Helvetica", "Arial"],
    "figure.facecolor": SURF, "axes.facecolor": SURF, "savefig.facecolor": SURF,
    "text.color": INK, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
    "axes.edgecolor": AXIS, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8,
    "axes.spines.top": False, "axes.spines.right": False, "axes.spines.left": False,
    "axes.titlesize": FS_TITLE, "axes.titleweight": "normal", "axes.titlelocation": "left", "axes.titlepad": 14,
    "axes.labelsize": FS_LABEL, "xtick.labelsize": FS_TICK, "ytick.labelsize": FS_TICK,
    "lines.linewidth": 2.0, "svg.fonttype": "none",
})

def rows(name):
    with open(D / name) as f:
        return list(csv.DictReader(f))

def fl(r, k, default=None):
    v = r.get(k, "")
    return float(v) if v not in ("", None) else default

def foot(ax, text, loc="lower left"):
    """Source note inside the axes area."""
    x, ha = (0.01, "left") if "left" in loc else (0.99, "right")
    y, va = (0.03, "bottom") if "lower" in loc else (0.97, "top")
    ax.text(x, y, text, transform=ax.transAxes, ha=ha, va=va, color=MUTED, fontsize=FS_FOOT)

def finish(fig, name):
    fig.savefig(HERE / name, format="svg", bbox_inches="tight", pad_inches=0.2, metadata={"Date": None})
    fig.savefig(HERE / name.replace(".svg", ".png"), format="png", dpi=160, bbox_inches="tight", pad_inches=0.2)
    plt.close(fig)
    print("wrote", name)

NUMBERS = {}

# ---------------------------------------------------------------- 1. vacuum holdback
r = rows("vacuum-holdback.csv")
t = [fl(x, "elapsed_s") / 60 for x in r]
dead = [fl(x, "dead_pct") for x in r]
av = [fl(x, "autovac") for x in r]
held = [i for i, x in enumerate(r) if x["tx_age_s"]]
k = held[-1]                                   # last sample with the holdback alive
t_open, t_kill = t[held[0]], t[k]
peak = max(dead); i_peak = dead.index(peak)
n_during = int(av[k] - av[held[0]])
NUMBERS["vacuum-holdback"] = dict(peak_pct=round(peak, 1), passes_while_open=n_during,
                                  open_min=round(t_open, 1), killed_min=round(t_kill, 1),
                                  reclaimed_to_pct=min(dead[k:k + 6]))
fig, (a1, a2) = plt.subplots(2, 1, figsize=(11, 5.6), sharex=True,
                             gridspec_kw={"height_ratios": [3, 1.5], "hspace": 0.10})
a1.plot(t, dead, color=S1)
for a in (a1, a2):
    a.axvspan(t_open, t_kill, color=S2, alpha=0.10, lw=0)
    a.grid(axis="x", visible=False)
a1.set_title(f"One idle transaction: {peak:.0f}% dead, {n_during} vacuum passes, nothing reclaimed")
a1.set_ylabel("dead tuples, % of table")
a1.set_ylim(0, peak * 1.22)
a1.text((t_open + t_kill) / 2, peak * 1.19, "session idle in transaction", ha="center", va="top", color=INK2, fontsize=FS_ANN)
a1.annotate(f"peak {peak:.0f}% dead", (t[i_peak], peak), xytext=(0, 6), textcoords="offset points",
            ha="center", va="bottom", color=INK, fontsize=FS_ANN)
a1.annotate("BEGIN; UPDATE ...; then idle", (t_open, dead[held[0]]), xytext=(6, 16), textcoords="offset points", color=INK2, fontsize=FS_ANN)
# session end: horizontal leader from the text to the drop line at y = 40
y_lead = 40.0
j = next(i for i in range(i_peak, len(dead)) if dead[i] < y_lead)
x_lead = t[j - 1] + (t[j] - t[j - 1]) * (dead[j - 1] - y_lead) / (dead[j - 1] - dead[j])
a1.annotate("session ended by\nidle_in_transaction_session_timeout;\nthe next vacuum pass reclaims",
            (x_lead, y_lead), xytext=(8.3, y_lead), textcoords="data", ha="left", va="center",
            color=INK2, fontsize=FS_ANN, arrowprops=dict(arrowstyle="-", color=MUTED, lw=1))
a2.step(t, av, where="post", color=S3)
a2.set_ylabel("passes (cum.)")
a2.set_xlabel("minutes")
a2.set_ylim(av[0] - 0.5, max(av) + 1.2)
a2.text(2.5, av[k] + 0.5, f"{n_during} passes while the transaction sat idle", ha="left", va="bottom", color=INK, fontsize=FS_ANN)
foot(a2, "pgbench_accounts, 100k rows, ~300 UPDATE/s, PostgreSQL 17", "upper left")
finish(fig, "vacuum-holdback.svg")

# ---------------------------------------------------------------- 2. the index that killed HOT
ni, wi = rows("high-bloat-no_index.csv"), rows("high-bloat-with_index.csv")
xmax = max(fl(x, "cum_updates") for x in wi) * 1.05
def series(rs):
    xs = [fl(x, "cum_updates") for x in rs]; ys = [fl(x, "dead_pct") for x in rs]
    return [x for x in xs if x <= xmax], [y for x, y in zip(xs, ys) if x <= xmax]
x1, y1 = series(ni); x2, y2 = series(wi)
plateau_plotted = sum(y1[-5:]) / 5                       # what the blue line shows at the right edge
final_no_index = fl(ni[-1], "dead_pct"); final_updates = fl(ni[-1], "cum_updates"); final_min = fl(ni[-1], "elapsed_s") / 60
NUMBERS["hot-index"] = dict(with_index_pct=y2[-1], with_index_updates=int(x2[-1]), no_index_pct_at_edge=round(plateau_plotted, 1),
                            no_index_final_pct=final_no_index, no_index_final_updates=int(final_updates), no_index_final_min=round(final_min))
fig, ax = plt.subplots(figsize=(11, 5.4))
ax.plot(x2, y2, color=S2, label="with an index on abalance (HOT impossible)")
ax.plot(x1, y1, color=S1, label="no index on abalance (HOT prunes in place)")
ax.set_title(f"One extra index: {y2[-1]:.0f}% dead vs {plateau_plotted:.0f}% after {x2[-1]/1000:.0f}k updates")
ax.set_xlabel("UPDATEs applied (autovacuum disabled on the table for both runs)        PostgreSQL 17, pgbench_accounts, 100k rows")
ax.set_ylabel("dead tuples, % of table")
ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v/1000:.0f}k"))
ax.set_xlim(0, xmax * 1.3); ax.set_ylim(0, max(y2) * 1.25)
ax.text(x2[-1] + xmax * 0.015, y2[-1], f"{y2[-1]:.0f}% dead\nafter {x2[-1]/1000:.0f}k updates", color=INK, va="center", fontsize=FS_ANN)
ax.text(x1[-1] + xmax * 0.015, y1[-1] + 0.4, f"{plateau_plotted:.1f}% at {x1[-1]/1000:.0f}k updates;\n{final_no_index:.1f}% after {final_updates/1e6:.1f}M updates and {final_min:.0f} minutes",
        color=INK, va="bottom", fontsize=FS_ANN)
ax.legend(loc="upper left", frameon=False, fontsize=FS_ANN, labelcolor=INK2)
ax.grid(axis="x", visible=False)
finish(fig, "hot-index.svg")

# ---------------------------------------------------------------- 3. connection storm vs rate limiter
r = rows("connection-churn-tuned.csv")
t = [fl(x, "elapsed_s") for x in r]
act = [fl(x, "actual") for x in r]; tgt = [fl(x, "target") for x in r]; rej = [fl(x, "rejections_cum") for x in r]
hi = [i for i, (a, g) in enumerate(zip(act, tgt)) if g >= max(tgt) - 1 and a >= 0.8 * g]
i0 = hi[0]; i1 = next((i for i in range(i0, len(act)) if act[i] < 0.5 * tgt[i]), len(act) - 1)
tail = [a for a in act[i1 + 4:] if a > 0]; avg = sum(tail) / len(tail)
burst_s = t[i1] - t[i0]
NUMBERS["connection-storm"] = dict(attempted_per_s=int(max(tgt)), burst_s=round(burst_s), accepted_after=round(avg), rejected_total=int(rej[-1]))
fig, (a1, a2) = plt.subplots(2, 1, figsize=(11, 5.6), sharex=True,
                             gridspec_kw={"height_ratios": [3, 1.5], "hspace": 0.10})
a1.plot(t, tgt, color=S2, lw=2.0, label="connections/s the app attempted")
a1.plot(t, act, color=S1, label="connections/s the database accepted")
a1.set_title(f"{max(tgt):.0f}/s attempted, {avg:.0f}/s accepted after {burst_s:.0f} s, {rej[-1]/1000:.0f}k rejected")
a1.set_ylabel("new connections / s")
a1.set_ylim(0, max(tgt) * 1.55)   # headroom so the legend clears the plateau annotation
a1.legend(loc="upper left", frameon=False, fontsize=FS_ANN, labelcolor=INK2, ncol=1)
a1.annotate(f"the limiter allows {max(tgt):.0f}/s for about {burst_s:.0f} s", ((t[i0] + t[i1]) / 2, max(tgt)), xytext=(0, 8),
            textcoords="offset points", ha="center", va="bottom", color=INK, fontsize=FS_ANN)
a1.annotate(f"then about {avg:.0f}/s, and most attempts are rejected", (t[i1 + 6], avg), xytext=(t[i1] + 12, max(tgt) * 0.62),
            textcoords="data", ha="left", va="bottom", color=INK, fontsize=FS_ANN,
            arrowprops=dict(arrowstyle="-", color=MUTED, lw=1))
a2.plot(t, rej, color=S3)
a2.set_ylabel("rejected (cum.)")
a2.set_xlabel("seconds")
a2.text(0.0, -0.62, "PostgreSQL 17; the limiter is max_connections, same shape everywhere", transform=a2.transAxes, ha="left", va="top", color=MUTED, fontsize=FS_FOOT)
a2.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v/1000:.0f}k"))
a2.set_ylim(0, rej[-1] * 1.35)
a2.text(t[-1], rej[-1] * 1.04, f"{rej[-1]/1000:.0f}k connection attempts rejected", color=INK, ha="right", va="bottom", fontsize=FS_ANN)
a2.set_xlim(0, t[-1] * 1.12)
for a in (a1, a2):
    a.grid(axis="x", visible=False)
finish(fig, "connection-storm.svg")

# ---------------------------------------------------------------- 3b. pooled vs unpooled: pgbench -C on local PG 17
# Source: charts/data/pgbench-churn.csv, raw pgbench output in charts/data/pgbench-churn/.
# PostgreSQL 17.10 on a 10-core Apple M5 laptop, unix sockets, pgbench -S (select-only), 20 clients,
# 10 threads, scale 10. "connect per transaction" is pgbench -C. Pooled runs go through pgbouncer
# 1.26 in transaction mode, default_pool_size 20. 2026-11-16.
r = rows("pgbench-churn.csv")
by = {x["run"]: x for x in r}
lad = sorted(int(x["requested_per_s"]) for x in r if x["requested_per_s"])
dir_ach = [fl(by[f"rate{q}_direct"], "tps") for q in lad]; pool_ach = [fl(by[f"rate{q}_pooled"], "tps") for q in lad]
dir_lat = [fl(by[f"rate{q}_direct"], "latency_avg_ms") for q in lad]; pool_lat = [fl(by[f"rate{q}_pooled"], "latency_avg_ms") for q in lad]
dir_max = [fl(by[f"rate{q}_direct"], "lag_max_ms") for q in lad]
pd_, pp_, cd_, cp_ = (fl(by[k], "tps") for k in ("persistent_direct", "persistent_pooled", "churn_direct", "churn_pooled"))
cd_ms, cp_ms = fl(by["churn_direct"], "connect_ms"), fl(by["churn_pooled"], "connect_ms")
NUMBERS["pooled-vs-unpooled"] = dict(persistent=int(pd_), churn_direct=int(cd_), churn_pooled=int(cp_), connect_ms_direct=cd_ms, connect_ms_pooled=cp_ms,
                                     top_rate=lad[-1], top_direct_latency_ms=dir_lat[-1], top_direct_lag_max_ms=dir_max[-1], top_pooled_latency_ms=pool_lat[-1])
def pooled_chart(name, series):
    """Three versions of the same picture, one per slide. "direct": only the connect-per-transaction run, so neither
    the pool nor pgbouncer is introduced before its slide. "persistent": adds the persistent bar (the app-side pool).
    "pgbouncer": adds the pgbouncer series and bar."""
    with_pgbouncer = series == "pgbouncer"
    with_persistent = series in ("persistent", "pgbouncer")
    fig, (b1, b2) = plt.subplots(1, 2, figsize=(11, 5.6), gridspec_kw={"width_ratios": [1.4, 1], "wspace": 0.30})
    if with_pgbouncer:
        title = f"pgbench, 20 clients, local PG 17: {cd_:,.0f}/s -C direct, {cp_:,.0f}/s -C through pgbouncer, {pd_:,.0f}/s persistent"
    elif with_persistent:
        title = f"pgbench, 20 clients, local PG 17: {cd_:,.0f}/s connecting per transaction, {pd_:,.0f}/s persistent"
    else:
        title = f"pgbench, 20 clients, local PG 17: {cd_:,.0f}/s connecting per transaction"
    fig.suptitle(title, x=0.01, y=0.99, ha="left", fontsize=FS_TITLE, color=INK)
    b1.plot(lad, dir_lat, color=S2, marker="o", label="connect per transaction (pgbench -C), direct to Postgres")
    if with_pgbouncer:
        b1.plot(lad, pool_lat, color=S1, marker="o", label="connect per transaction, through pgbouncer")
    b1.set_xscale("log", base=2); b1.set_yscale("log")
    b1.set_xticks(lad); b1.set_xticklabels([f"{q:,}" for q in lad]); b1.minorticks_off()
    b1.set_yticks([1, 10, 100, 1000]); b1.set_yticklabels(["1 ms", "10 ms", "100 ms", "1 s"])
    b1.set_ylim(1, 3000); b1.set_xlim(lad[0] * 0.8, lad[-1] * 1.3)
    b1.set_xlabel("connections per second requested (pgbench -R)"); b1.set_ylabel("average latency")
    b1.annotate(f"{dir_lat[-1]:.0f} ms average, {dir_max[-1]/1000:.1f} s worst case\nthe server is connecting as fast\nas it can, {dir_ach[-1]:,.0f} a second",
                (lad[-1], dir_lat[-1]), xytext=(lad[0] * 1.1, 400), textcoords="data", ha="left", va="center", color=INK, fontsize=FS_ANN,
                arrowprops=dict(arrowstyle="-", color=MUTED, lw=1))
    if with_pgbouncer:
        b1.annotate(f"{pool_lat[-1]:.1f} ms", (lad[-1], pool_lat[-1]), xytext=(8, 0), textcoords="offset points", ha="left", va="center", color=INK, fontsize=FS_ANN)
    b1.grid(axis="x", visible=False)
    if with_pgbouncer:
        labels, vals, cols = ["-C direct", "-C through\npgbouncer", "persistent"], [cd_, cp_, pd_], [S2, S1, S3]
        notes = [f"{cd_ms:.1f} ms per connect", f"{cp_ms:.1f} ms per connect", ""]
    elif with_persistent:
        labels, vals, cols = ["connect per\ntransaction (-C)", "persistent"], [cd_, pd_], [S2, S3]
        notes = [f"{cd_ms:.1f} ms per connect", ""]
    else:
        labels, vals, cols = ["connect per\ntransaction (-C)"], [cd_], [S2]
        notes = [f"{cd_ms:.1f} ms per connect"]
    bars = b2.bar(labels, vals, color=cols, width=0.6)
    b2.set_yscale("log"); b2.set_ylabel("transactions per second"); b2.grid(axis="x", visible=False); b2.minorticks_off()
    b2.set_yticks([1000, 10000, 100000]); b2.set_yticklabels(["1k", "10k", "100k"])
    for bar, v, note in zip(bars, vals, notes):
        b2.text(bar.get_x() + bar.get_width() / 2, v * 1.15, f"{v:,.0f}/s" + (f"\n{note}" if note else ""), ha="center", va="bottom", color=INK, fontsize=FS_ANN)
    b2.set_ylim(500, pd_ * 12)
    if not with_persistent:
        b2.set_xlim(-0.6, 1.6)          # same bar footprint as the two-bar chart that follows it
    foot_ = "PostgreSQL 17.10, 10-core laptop, unix sockets, select-only, scale 10 (1,000,000 rows)."
    if with_pgbouncer:
        foot_ += " pgbouncer 1.26, transaction mode, pool 20."
    fig.text(0.01, 0.01, foot_, ha="left", va="bottom", color=MUTED, fontsize=FS_FOOT)
    fig.subplots_adjust(top=0.86, bottom=0.2)
    finish(fig, name)
pooled_chart("connection-direct-only.svg", "direct")
pooled_chart("connection-pooled-direct.svg", "persistent")
pooled_chart("connection-pooled.svg", "pgbouncer")

# ---------------------------------------------------------------- 3c. unused indexes: a timeline, with the two numbers that move
# Illustrative, not measured: the sequence every team lives through. Latency and connections
# in use are drawn to the shape of the story; the index count and the events are the content.
years = [2021, 2021.5, 2022, 2022.5, 2023, 2023.5, 2024, 2024.5, 2025, 2025.5, 2026]
idx   = [1,    2,      2,    2,      5,    5,      7,    7,      7,    7,      7]
lat   = [1.2,  1.4,    1.4,  1.5,    2.3,  2.5,    3.2,  3.5,    3.9,  4.3,    4.8]
conns = [18,   20,     20,   22,     31,   34,     44,   48,     54,   58,     60]
events = [(2021.5, "a slow query,\nsomeone adds an index", 1), (2022, "the query changes,\nthe index stays", 0),
          (2023, "the ORM adds an index\non every foreign key", 1), (2024, "just in case,\n(a), (a, b), (a, b, c)", 0)]
fig, (t1, t2) = plt.subplots(2, 1, figsize=(11, 5.2), sharex=True, gridspec_kw={"height_ratios": [1.15, 2.2], "hspace": 0.1})
t1.step(years, idx, where="post", color=S3, lw=2.2)
t1.set_ylim(0, 10.5); t1.set_yticks([1, 4, 7]); t1.set_ylabel("indexes"); t1.grid(axis="x", visible=False)
for x, label, up in events:
    t1.axvline(x, color=MUTED, lw=0.8, ls=":"); t2.axvline(x, color=MUTED, lw=0.8, ls=":")
    t1.annotate(label, (x, 10.3 if up else 0.4), xytext=(5, 0), textcoords="offset points", ha="left", va="top" if up else "bottom", color=INK, fontsize=FS_ANN - 2, linespacing=1.1)
t2.plot(years, lat, color=S2, lw=2.2)
t2.set_ylabel("UPDATE p50, ms", color=S2); t2.set_ylim(0, 6); t2.grid(axis="x", visible=False)
t3 = t2.twinx(); t3.plot(years, conns, color=S1, lw=2.2)
t3.axhline(60, color=S1, lw=1, ls="--"); t3.text(2021.0, 61, "pool size", color=S1, va="bottom", fontsize=FS_ANN - 1)
t3.set_ylabel("connections in use", color=S1); t3.set_ylim(0, 72); t3.grid(False); t3.spines["top"].set_visible(False)
t2.set_xticks([2021, 2022, 2023, 2024, 2025, 2026]); t2.set_xticklabels([str(y) for y in range(2021, 2027)]); t2.set_xlim(2020.9, 2026.4)
foot(t2, "same traffic throughout. Illustrative shape, not a measurement", loc="lower right")
finish(fig, "index-timeline.svg")

# ---------------------------------------------------------------- 4. bulk DELETE: indexes thin, they do not shrink
# Source: autovacuum log lines from a production PostgreSQL 14 database, 2026-05-07 vs 2026-10-06;
# in-tree B-tree pages per live row. Rows fell 62% (347M -> 131M) under a batched DELETE GC.
# Names generalised for a public deck.
IDX = [  # (label, kind, may, oct)
    ("updated_at  (rewritten on UPDATE, so random in practice)", "rand", 0.00355, 0.01790),
    ("primary key  (uuid)",                     "rand", 0.00521, 0.01412),
    ("next_id  (uuid)",                         "rand", 0.00185, 0.00346),
    ("branch_id  (uuid)",                       "rand", 0.00226, 0.00406),
    ("endpoint_id  (uuid)",                     "rand", 0.00216, 0.00388),
    ("project_id, status  (uuid, int)",         "rand", 0.00183, 0.00298),
    ("project_id  (uuid)",                      "rand", 0.00205, 0.00325),
    ("branch_id, created_at  (uuid, time)",     "time", 0.01482, 0.01500),
    ("created_at  (time)",                      "time", 0.00664, 0.00617),
    ("project_id, created_at  (uuid, time)",    "time", 0.01407, 0.01309),
    ("gc job: created_at, ...  (time first)",   "time", 0.01375, 0.01254),
]
def pct(r): return (r[3] - r[2]) / r[2] * 100
IDX.sort(key=lambda r: (r[1] != "rand", -pct(r)))      # random-key group first, biggest growth first
n = len(IDX); ys = [n - 1 - i for i in range(n)]       # first entry at the top
fig, ax = plt.subplots(figsize=(11, 5.4))
for y, rr in zip(ys, IDX):
    lab, kind, a, b = rr
    ax.plot([a * 1000, b * 1000], [y, y], color=AXIS, lw=3, solid_capstyle="round", zorder=1)
    ax.scatter([a * 1000], [y], s=80, facecolors="none", edgecolors=INK2, linewidths=1.8, zorder=3)
    ax.scatter([b * 1000], [y], s=80, color=S2, zorder=3, edgecolors=SURF, linewidths=1.5)
    p = pct(rr)
    ax.text(max(a, b) * 1000 + 0.45, y, f"{p:+.0f}%", va="center", color=INK if p > 20 else INK2, fontsize=FS_ANN)
ax.set_yticks(ys); ax.set_yticklabels([r[0] for r in IDX], fontsize=12)
ax.set_xlabel("B-tree pages per 1,000 live rows      (production PostgreSQL 14, autovacuum logs, May vs Oct 2026)")
ax.set_title("DELETE 62% of the rows: random-key indexes keep almost all of their pages")
ax.scatter([], [], s=80, facecolors="none", edgecolors=INK2, linewidths=1.8, label="before: 347M rows (May)")
ax.scatter([], [], s=80, color=S2, label="after: 131M rows (Oct), 5 months of batched DELETE")
ax.legend(loc="upper center", bbox_to_anchor=(0.5, 1.0), ncol=2, frameon=False, fontsize=FS_ANN, labelcolor=INK2)
ax.set_xlim(0, 24); ax.set_ylim(-0.7, n - 0.3 + 1.2)   # headroom for the legend
ax.grid(axis="y", visible=False)
rand_ys = [y for y, rr in zip(ys, IDX) if rr[1] == "rand"]; time_ys = [y for y, rr in zip(ys, IDX) if rr[1] != "rand"]
ax.text(23.8, sum(rand_ys) / len(rand_ys) - 0.6, "random-key indexes:\nevery page loses a few entries,\nno page ever empties",
        ha="right", va="center", color=INK2, fontsize=FS_ANN)
ax.text(23.8, sum(time_ys) / len(time_ys), "time-ordered indexes:\ndeletes empty whole pages,\nvacuum recycles them",
        ha="right", va="center", color=INK2, fontsize=FS_ANN)
finish(fig, "index-thinning.svg")

import json
(HERE / "numbers.json").write_text(json.dumps(NUMBERS, indent=1))
print(json.dumps(NUMBERS))
