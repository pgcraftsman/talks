"""Render charts/pool-bloat.svg and inline it into deck/slides.md between the pool-bloat markers.

The OCONN animation (make_pool_exhaustion.py) retold for Mistake #1 (2026-11-18): no external service. The users table
bloats, the same query reads more pages every week, each query holds its server connection longer, the pool opens more
connections which fill the same way, and the app instances fail one by one. Nothing recovers on its own. Ids are
prefixed pb so the pool animations can share one HTML page.

Run: python3 -I make_pool_bloat.py   (any cwd; build.sh runs it before renumber)
"""
import pathlib, re

INK, INK2, MUTED, SURF, AXIS = "#f0efec", "#c3c2b7", "#898781", "#1a1a19", "#383835"
S1, S2, S3, AMBER, RED = "#3987e5", "#d95926", "#199e70", "#e0a52a", "#e5484d"
W, H = 1100, 450
HOLD = 2.0
START, MAXC, BATCH = 5, 20, 4
FIRST_GAP = 0.5
FILL_GAP = 0.8
BATCH_PAUSE = 0.6
FAIL_GAP = 0.7

# ---- timeline
BLIPS = [(1, HOLD + 0.8, HOLD + 1.1), (3, HOLD + 1.9, HOLD + 2.2), (0, HOLD + 3.0, HOLD + 3.3), (2, HOLD + 3.1, HOLD + 3.4)]
t_slow = HOLD + 4.6                           # the table starts to bloat
t_held = {i: t_slow + 0.6 + FIRST_GAP * i for i in range(START)}
t_open = {}
t = t_held[START - 1] + BATCH_PAUSE
k = START
while k < MAXC:
    batch = list(range(k, min(k + BATCH, MAXC)))
    for j in batch:
        t_open[j] = t
    for n, j in enumerate(batch):
        t_held[j] = t + 0.5 + FILL_GAP * n
    t = t_held[batch[-1]] + BATCH_PAUSE
    k += BATCH
t_exhausted = t
APP_Y = (70, 150, 230)
t_fail = [t_exhausted + FAIL_GAP * i for i in range(len(APP_Y))]
t_end = t_fail[-1] + 1.5
P = round(t_end + 3.0, 1)

anims = []
def sched(target, attr, steps):
    vals, kts = [], []
    for n, (ts, v) in enumerate(steps):
        if n > 0:
            vals.append(steps[n - 1][1]); kts.append(max(0.0, ts - 0.05) / P)
        vals.append(v); kts.append(ts / P)
    vals.append(steps[-1][1]); kts.append(1.0)
    anims.append(f'<animate href="#{target}" attributeName="{attr}" values="{";".join(str(v) for v in vals)}" '
                 f'keyTimes="{";".join(f"{x:.4f}" for x in kts)}" calcMode="discrete" dur="{P}s" repeatCount="indefinite"/>')

o = [f'<svg xmlns="http://www.w3.org/2000/svg" id="pool-bloat-svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="DejaVu Sans, system-ui, sans-serif">',
     f'<rect width="{W}" height="{H}" fill="{SURF}"/>']
ids = {}
def uid(prefix):
    ids[prefix] = ids.get(prefix, 0) + 1
    return f"pb-{prefix}{ids[prefix]}"
def text(x, y, s, size=14, fill=INK, anchor="start", id=None, opacity=None):
    i = f' id="{id}"' if id else ""; op = f' opacity="{opacity}"' if opacity is not None else ""
    o.append(f'<text{i} x="{x}" y="{y}" fill="{fill}" font-size="{size}" text-anchor="{anchor}"{op}>{s}</text>')
def rect(x, y, w, h, color, op=0.14, rx=8, id=None, sw=1.5, stroke=None, opacity=None):
    i = f' id="{id}"' if id else ""; vis = f' opacity="{opacity}"' if opacity is not None else ""
    o.append(f'<rect{i} x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{color}" fill-opacity="{op}" stroke="{stroke or color}" stroke-width="{sw}"{vis}/>')

# ---- geometry (same as make_pool_exhaustion.py)
PX, PY, PW, PH = 380, 44, 460, 340
AX, AW = 110, 150
TBX, TBY = 20, 318                            # the users table box, where the payments API sat
APPS = len(APP_Y)
RX, RY = PW / 2, 18
cxp = PX + PW / 2
top, bot = PY + RY, PY + PH
SX, SY, SW, SH, GX, GY = PX + 30, top + 62, 60, 44, 24, 18
def slot_xy(k):
    return SX + (k % 5) * (SW + GX), SY + (k // 5) * (SH + GY)
per_app = [sorted(k for k in range(MAXC) if k % APPS == a) for a in range(APPS)]
def line_ends(k):
    a = k % APPS; j = per_app[a].index(k); n = len(per_app[a])
    ya = APP_Y[a] + 6 + j * (44 / max(1, n - 1)); yb = PY + 36 + a * 96 + j * (70 / max(1, n - 1))
    return ya, yb

# ---- app instances
for i, y in enumerate(APP_Y):
    rect(AX, y, AW, 56, S1, op=0.12)
    text(AX + AW / 2, y + 25, "app instance", 14, anchor="middle"); text(AX + AW / 2, y + 44, "pool of 20 clients", 12, INK2, "middle")

# ---- the users table: one page per row, then more every week, never fewer
rect(TBX, TBY, AW, 56, S3, id="pb-tbl")
sched("pb-tbl", "fill", [(0, RED), (HOLD, S3), (t_slow, AMBER), (t_held[13], RED)])
sched("pb-tbl", "stroke", [(0, RED), (HOLD, S3), (t_slow, AMBER), (t_held[13], RED)])
text(TBX + AW / 2, TBY + 24, "users table", 14, anchor="middle")
text(TBX + AW / 2, TBY + 43, "1 page per row", 12, S3, "middle", id="pb-pg-ok"); sched("pb-pg-ok", "opacity", [(0, 0), (HOLD, 1), (t_slow, 0)])
steps = [("20 pages per row", t_slow), ("80 pages per row", t_held[5]), ("150 pages per row", t_held[9]), ("221 pages per row", t_held[13])]
for n, (label, ta) in enumerate(steps):
    last = n == len(steps) - 1
    tid = uid("pg"); text(TBX + AW / 2, TBY + 43, label, 12, RED if last else AMBER, "middle", id=tid, opacity=0)
    sched(tid, "opacity", [(0, 1 if last else 0), (HOLD, 0), (ta, 1)] + ([] if last else [(steps[n + 1][1], 0)]))

# ---- connections: line app to database (green free, orange busy)
for k in range(MAXC):
    ya, yb = line_ends(k)
    lid = uid("ln"); o.append(f'<line id="{lid}" x1="{AX + AW}" y1="{ya:.0f}" x2="{PX}" y2="{yb:.0f}" stroke="{S2}" stroke-width="1.3"/>')
    sched(lid, "stroke", [(0, S2), (HOLD, S3), (t_held[k], S2)])
    if k >= START:
        sched(lid, "opacity", [(0, 1), (HOLD, 0), (t_open[k], 1)])

# ---- the database
o.append(f'<path d="M {PX},{top} V {bot} A {RX},{RY} 0 0 0 {PX+PW},{bot} V {top}" fill="{S3}" fill-opacity="0.08" stroke="{S3}" stroke-width="1.5"/>')
o.append(f'<ellipse cx="{cxp}" cy="{top}" rx="{RX}" ry="{RY}" fill="{S3}" fill-opacity="0.22" stroke="{S3}" stroke-width="1.5"/>')
text(cxp, top + 44, f"Postgres: {START} server connections, grows to {MAXC}", 15, anchor="middle")
for k in range(MAXC):
    x, y = slot_xy(k)
    sid = uid("slot"); rect(x, y, SW, SH, S2, op=0.8, rx=6, id=sid)
    sched(sid, "fill", [(0, S2), (HOLD, S3), (t_held[k], S2)]); sched(sid, "stroke", [(0, S2), (HOLD, S3), (t_held[k], S2)])
    lab = uid("lab"); text(x + SW / 2, y + SH / 2 + 4, "query", 10, anchor="middle", id=lab)
    sched(lab, "opacity", [(0, 1), (HOLD, 0), (t_held[k], 1)])
    if k >= START:
        sched(sid, "opacity", [(0, 1), (HOLD, 0), (t_open[k], 1)])
        new = uid("new"); text(x + SW / 2, y + SH / 2 + 4, "new", 10, anchor="middle", id=new, opacity=0)
        sched(new, "opacity", [(0, 0), (t_open[k], 1), (t_held[k], 0)])
text(PX + 30, bot - 10, "green: free", 12, S3); text(PX + 150, bot - 10, "orange: busy, reading dead versions to find the live row", 12, S2)

# ---- healthy-phase blips: a query takes a millisecond
for k, ta, tb in BLIPS:
    x, y = slot_xy(k); ya, yb = line_ends(k)
    bs = uid("bslot"); rect(x, y, SW, SH, S2, op=0.8, rx=6, id=bs, opacity=0); sched(bs, "opacity", [(0, 0), (ta, 1), (tb, 0)])
    bl = uid("blab"); text(x + SW / 2, y + SH / 2 + 4, "query", 10, anchor="middle", id=bl, opacity=0); sched(bl, "opacity", [(0, 0), (ta, 1), (tb, 0)])
    bn = uid("bln"); o.append(f'<line id="{bn}" x1="{AX + AW}" y1="{ya:.0f}" x2="{PX}" y2="{yb:.0f}" stroke="{S2}" stroke-width="1.3" opacity="0"/>'); sched(bn, "opacity", [(0, 0), (ta, 1), (tb, 0)])

# ---- app failure once the pool is exhausted
for i, y in enumerate(APP_Y):
    fr = uid("fail"); rect(AX, y, AW, 56, RED, op=0.18, id=fr, sw=2); sched(fr, "opacity", [(0, 1), (HOLD, 0), (t_fail[i], 1)])
    fl = uid("strike"); o.append(f'<line id="{fl}" x1="{AX + 4}" y1="{y + 52}" x2="{AX + AW - 4}" y2="{y + 4}" stroke="{RED}" stroke-width="3"/>'); sched(fl, "opacity", [(0, 1), (HOLD, 0), (t_fail[i], 1)])

# ---- captions
caps = [("every query reads one page, holds its connection for a millisecond, and gives it back", (HOLD, t_slow)),
        ("the table bloats. The same query reads 20 pages, then 80. Each one holds its connection longer", (t_slow, t_held[START - 1] + BATCH_PAUSE)),
        ("no free connection, so the pool opens a few more. They fill the same way: same traffic, longer holds", (t_held[START - 1] + BATCH_PAUSE, t_exhausted)),
        ("every server connection is busy reading dead versions. The pool is exhausted and the app is down", (t_exhausted, t_end))]
for s, (a, b) in caps:
    cid = uid("cap"); text(20, H - 12, s, 15, id=cid, opacity=0); sched(cid, "opacity", [(0, 0), (a, 1), (b, 0)])
cid = uid("cap"); text(20, H - 12, "221 pages per row. The database is saturated, the app is down, and not a line of code changed", 15, id=cid)
sched(cid, "opacity", [(0, 1), (HOLD, 0), (t_end, 1)])

# ---- controls (inline HTML deck only). Same keys as the other pool animations
rect(W - 96, 10, 86, 28, SURF, op=1, rx=6, sw=1.2, stroke=AXIS)
text(W - 53, 29, "pause (a)", 13, INK2, "middle", id="pb-ctl-label")
rect(W - 192, 10, 86, 28, SURF, op=1, rx=6, sw=1.2, stroke=AXIS)
text(W - 149, 29, "restart (r)", 13, INK2, "middle")
o += anims
o.append(f'<rect id="pb-ctl" x="{W - 96}" y="10" width="86" height="28" rx="6" fill="transparent" cursor="pointer"/>')
o.append(f'<rect id="pb-ctl-restart" x="{W - 192}" y="10" width="86" height="28" rx="6" fill="transparent" cursor="pointer"/>')
o.append('<script>'
         '(function(){var svg=document.getElementById("pool-bloat-svg");if(!svg||!svg.pauseAnimations)return;'
         'var paused=false,label=document.getElementById("pb-ctl-label");'
         'function toggle(){paused=!paused;if(paused){svg.pauseAnimations();}else{svg.unpauseAnimations();}label.textContent=paused?"resume (a)":"pause (a)";}'
         'function restart(){svg.setCurrentTime(0);if(paused){svg.pauseAnimations();}else{svg.unpauseAnimations();}}'
         'document.getElementById("pb-ctl").addEventListener("click",toggle);'
         'document.getElementById("pb-ctl-restart").addEventListener("click",restart);'
         'document.addEventListener("keydown",function(e){if(e.key==="a"){toggle();}else if(e.key==="r"){restart();}});})();'
         '</script>')
o.append("</svg>")
svg = "\n".join(o) + "\n"

here = pathlib.Path(__file__).resolve().parent
(here / "pool-bloat.svg").write_text(svg)
deck = here.parent / "deck" / "slides.md"
md = deck.read_text()
inline = svg.replace(f'width="{W}" height="{H}"', 'width="1150" height="470"', 1).rstrip("\n")
block = "<!-- pool-bloat:begin (generated by charts/make_pool_bloat.py; do not edit by hand) -->\n" + inline + "\n<!-- pool-bloat:end -->"
if "<!-- pool-bloat:begin" not in md:
    raise SystemExit("slides.md has no pool-bloat markers")
md = re.sub(r"<!-- pool-bloat:begin.*?<!-- pool-bloat:end -->", lambda m: block, md, flags=re.S)
deck.write_text(md)
print(f"wrote pool-bloat.svg and the inline copy: period {P}s, bloat at {t_slow:.1f}s, exhausted at {t_exhausted:.1f}s, {len(anims)} animations")
