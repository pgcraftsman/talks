"""Render charts/pool-exhaustion.svg and inline it into deck/slides.md between markers.

Run: python3 -I make_pool_exhaustion.py   (any cwd; build.sh runs it before renumber)

Story. A connection pool opens with START server connections. While the payments API answers
in 50 ms, transactions open, call it, and commit: a connection flips to idle in transaction for
a moment and comes back. Then the API slows down. Each call holds its transaction, and with it
a server connection; with none free the pool opens a batch of BATCH more, which fill the same
way, until MAXC are held. The app instances fail one by one. The API recovers; nothing else does.

Timing. SMIL with every attribute on one period P, repeating, so the animation is running
whenever the slide comes up. The end state (API recovered, everything else stuck) is held for
HOLD seconds at the top of each cycle, which is also the frame the PDF and PNG exports capture.

Markup. Marp's HTML pass rewrites a closing </rect> into a stray <rect />, so shapes carry no
children: every shape has an id and every <animate> targets it with href. The pause control
and its script only work in the HTML deck, where the SVG is inline.
"""
import pathlib, re

INK, INK2, MUTED, SURF, AXIS = "#f0efec", "#c3c2b7", "#898781", "#1a1a19", "#383835"
S1, S2, S3, AMBER, RED = "#3987e5", "#d95926", "#199e70", "#e0a52a", "#e5484d"
W, H = 1100, 450
HOLD = 2.0
START, MAXC, BATCH = 5, 20, 4
FIRST_GAP = 0.5      # seconds between the first START connections going idle
FILL_GAP = 0.8       # seconds between new connections going idle, within a batch
BATCH_PAUSE = 0.6    # seconds from the last held to the next batch opening
FAIL_GAP = 0.7       # seconds between app instances failing once the pool is exhausted

# ---- timeline
# healthy phase: (connection, from, to) brief flips to idle in transaction that commit and clear
BLIPS = [(1, HOLD + 0.8, HOLD + 1.5), (3, HOLD + 1.9, HOLD + 2.6), (0, HOLD + 3.0, HOLD + 3.6), (2, HOLD + 3.1, HOLD + 3.8)]
t_slow = HOLD + 4.6                           # the payments API starts to slow down
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
t_recover = t_fail[-1] + 1.5
P = round(t_recover + 3.0, 1)

# ---- SMIL helpers: one discrete, repeating animation per (element, attribute)
anims = []
def sched(target, attr, steps):
    """steps: [(time, value), ...] starting at time 0; a value holds until the next step, and
    the last value holds to the end of the period."""
    vals, kts = [], []
    for n, (ts, v) in enumerate(steps):
        if n > 0:
            vals.append(steps[n - 1][1]); kts.append(max(0.0, ts - 0.05) / P)
        vals.append(v); kts.append(ts / P)
    vals.append(steps[-1][1]); kts.append(1.0)
    anims.append(f'<animate href="#{target}" attributeName="{attr}" values="{";".join(str(v) for v in vals)}" '
                 f'keyTimes="{";".join(f"{x:.4f}" for x in kts)}" calcMode="discrete" dur="{P}s" repeatCount="indefinite"/>')

o = [f'<svg xmlns="http://www.w3.org/2000/svg" id="pool-svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="DejaVu Sans, system-ui, sans-serif">',
     f'<rect width="{W}" height="{H}" fill="{SURF}"/>']
ids = {}
def uid(prefix):
    ids[prefix] = ids.get(prefix, 0) + 1
    return f"{prefix}{ids[prefix]}"
def text(x, y, s, size=14, fill=INK, anchor="start", id=None, opacity=None):
    i = f' id="{id}"' if id else ""; op = f' opacity="{opacity}"' if opacity is not None else ""
    o.append(f'<text{i} x="{x}" y="{y}" fill="{fill}" font-size="{size}" text-anchor="{anchor}"{op}>{s}</text>')
def rect(x, y, w, h, color, op=0.14, rx=8, id=None, sw=1.5, stroke=None, opacity=None):
    i = f' id="{id}"' if id else ""; vis = f' opacity="{opacity}"' if opacity is not None else ""
    o.append(f'<rect{i} x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{color}" fill-opacity="{op}" stroke="{stroke or color}" stroke-width="{sw}"{vis}/>')

# ---- geometry
PX, PY, PW, PH = 380, 44, 460, 340          # the database cylinder
AX, AW = 110, 150                            # app column
APX = 20                                     # the payments API stays at the left edge
API_Y = 318
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
def call_path(k):
    ya, _ = line_ends(k); gx = 34 + (k % 5) * 8; xe = APX + 12 + k * ((AW - 24) / (MAXC - 1))
    return f"M {AX},{ya:.0f} C {gx},{ya:.0f} {gx},{API_Y - 6} {xe:.0f},{API_Y}"

# ---- app instances
for i, y in enumerate(APP_Y):
    rect(AX, y, AW, 56, S1, op=0.12)
    text(AX + AW / 2, y + 25, "app instance", 14, anchor="middle"); text(AX + AW / 2, y + 44, "pool of 20 clients", 12, INK2, "middle")

# ---- payments API: green, then slow (amber) from t_slow until it recovers
rect(APX, API_Y, AW, 56, S3, id="api")
sched("api", "fill", [(0, S3), (t_slow, AMBER), (t_recover, S3)])
sched("api", "stroke", [(0, S3), (t_slow, AMBER), (t_recover, S3)])
text(APX + AW / 2, API_Y + 24, "payments API", 14, anchor="middle")
text(APX + AW / 2, API_Y + 43, "response: 50 ms", 12, S3, "middle", id="rt-ok")
sched("rt-ok", "opacity", [(0, 1), (t_slow, 0), (t_recover, 1)])
steps = [("200 ms", t_slow), ("800 ms", t_held[5]), ("2 s", t_held[9]), ("5 s", t_held[13]), ("10 s", t_held[17]), ("20 s", t_held[19])]
for n, (label, ta) in enumerate(steps):
    tb = steps[n + 1][1] if n < len(steps) - 1 else t_recover
    tid = uid("rt"); text(APX + AW / 2, API_Y + 43, f"response: {label}", 12, RED if n == len(steps) - 1 else AMBER, "middle", id=tid, opacity=0)
    sched(tid, "opacity", [(0, 0), (ta, 1), (tb, 0)])

# ---- connections: line app to database (green serving, red held), call to the API (amber while slow)
for k in range(MAXC):
    ya, yb = line_ends(k)
    lid = uid("ln"); o.append(f'<line id="{lid}" x1="{AX + AW}" y1="{ya:.0f}" x2="{PX}" y2="{yb:.0f}" stroke="{RED}" stroke-width="1.3"/>')
    sched(lid, "stroke", [(0, RED), (HOLD, S3), (t_held[k], RED)])
    if k >= START:
        sched(lid, "opacity", [(0, 1), (HOLD, 0), (t_open[k], 1)])
    pid = uid("call"); o.append(f'<path id="{pid}" d="{call_path(k)}" fill="none" stroke="{AMBER}" stroke-width="1.2" stroke-dasharray="4 3"/>')
    sched(pid, "opacity", [(0, 1), (HOLD, 0), (t_held[k], 1)])

# ---- the database, drawn as a cylinder around its server connections
o.append(f'<path d="M {PX},{top} V {bot} A {RX},{RY} 0 0 0 {PX+PW},{bot} V {top}" fill="{S3}" fill-opacity="0.08" stroke="{S3}" stroke-width="1.5"/>')
o.append(f'<ellipse cx="{cxp}" cy="{top}" rx="{RX}" ry="{RY}" fill="{S3}" fill-opacity="0.22" stroke="{S3}" stroke-width="1.5"/>')
text(cxp, top + 44, f"Postgres: {START} server connections, grows to {MAXC}", 15, anchor="middle")
for k in range(MAXC):
    x, y = slot_xy(k)
    sid = uid("slot"); rect(x, y, SW, SH, S2, op=0.8, rx=6, id=sid)
    sched(sid, "fill", [(0, S2), (HOLD, S3), (t_held[k], S2)]); sched(sid, "stroke", [(0, S2), (HOLD, S3), (t_held[k], S2)])
    lab = uid("lab"); text(x + SW / 2, y + SH / 2 + 4, "idle in txn", 10, anchor="middle", id=lab)
    sched(lab, "opacity", [(0, 1), (HOLD, 0), (t_held[k], 1)])
    if k >= START:
        sched(sid, "opacity", [(0, 1), (HOLD, 0), (t_open[k], 1)])
        new = uid("new"); text(x + SW / 2, y + SH / 2 + 4, "new", 10, anchor="middle", id=new, opacity=0)
        sched(new, "opacity", [(0, 0), (t_open[k], 1), (t_held[k], 0)])
text(PX + 30, bot - 10, "green: serving requests", 12, S3); text(PX + 230, bot - 10, "orange: held by a transaction waiting on HTTP", 12, S2)

# ---- healthy-phase blips: overlays showing a connection briefly idle in transaction, then committed
for k, ta, tb in BLIPS:
    x, y = slot_xy(k); ya, yb = line_ends(k)
    bs = uid("bslot"); rect(x, y, SW, SH, S2, op=0.8, rx=6, id=bs, opacity=0); sched(bs, "opacity", [(0, 0), (ta, 1), (tb, 0)])
    bl = uid("blab"); text(x + SW / 2, y + SH / 2 + 4, "idle in txn", 10, anchor="middle", id=bl, opacity=0); sched(bl, "opacity", [(0, 0), (ta, 1), (tb, 0)])
    bn = uid("bln"); o.append(f'<line id="{bn}" x1="{AX + AW}" y1="{ya:.0f}" x2="{PX}" y2="{yb:.0f}" stroke="{RED}" stroke-width="1.3" opacity="0"/>'); sched(bn, "opacity", [(0, 0), (ta, 1), (tb, 0)])
    bc = uid("bcall"); o.append(f'<path id="{bc}" d="{call_path(k)}" fill="none" stroke="{S3}" stroke-width="1.2" stroke-dasharray="4 3" opacity="0"/>'); sched(bc, "opacity", [(0, 0), (ta, 1), (tb, 0)])

# ---- app failure: red box and a diagonal strike once the pool is exhausted
for i, y in enumerate(APP_Y):
    fr = uid("fail"); rect(AX, y, AW, 56, RED, op=0.18, id=fr, sw=2); sched(fr, "opacity", [(0, 1), (HOLD, 0), (t_fail[i], 1)])
    fl = uid("strike"); o.append(f'<line id="{fl}" x1="{AX + 4}" y1="{y + 52}" x2="{AX + AW - 4}" y2="{y + 4}" stroke="{RED}" stroke-width="3"/>'); sched(fl, "opacity", [(0, 1), (HOLD, 0), (t_fail[i], 1)])

# ---- captions
caps = [("transactions open, call the payments API, and commit in 50 ms. A connection is idle in transaction for a moment, then free", (HOLD, t_slow)),
        ("the payments API slows down. A request opens a transaction, calls it, and holds its server connection while it waits", (t_slow, t_held[START - 1] + BATCH_PAUSE)),
        ("no free connection, so the pool opens a few more. Each request calls the API inside its transaction, and holds one", (t_held[START - 1] + BATCH_PAUSE, t_exhausted)),
        ("every server connection is held by a transaction waiting on HTTP. The pool is exhausted and the database is idle", (t_exhausted, t_recover))]
for s, (a, b) in caps:
    cid = uid("cap"); text(20, H - 12, s, 15, id=cid, opacity=0); sched(cid, "opacity", [(0, 0), (a, 1), (b, 0)])
cid = uid("cap"); text(20, H - 12, "the payments API recovers. Every connection is still held and every app instance is still stuck", 15, id=cid)
sched(cid, "opacity", [(0, 1), (HOLD, 0), (t_recover, 1)])

# ---- pause / resume and restart controls (inline HTML deck only). Keys a and r; the mvcc primer uses n, b, a
rect(W - 96, 10, 86, 28, SURF, op=1, rx=6, sw=1.2, stroke=AXIS)
text(W - 53, 29, "pause (a)", 13, INK2, "middle", id="ctl-label")
rect(W - 192, 10, 86, 28, SURF, op=1, rx=6, sw=1.2, stroke=AXIS)
text(W - 149, 29, "restart (r)", 13, INK2, "middle")
o += anims
o.append(f'<rect id="ctl" x="{W - 96}" y="10" width="86" height="28" rx="6" fill="transparent" cursor="pointer"/>')
o.append(f'<rect id="ctl-restart" x="{W - 192}" y="10" width="86" height="28" rx="6" fill="transparent" cursor="pointer"/>')
o.append('<script>'
         '(function(){var svg=document.getElementById("pool-svg");if(!svg||!svg.pauseAnimations)return;'
         'var paused=false,label=document.getElementById("ctl-label");'
         'function toggle(){paused=!paused;if(paused){svg.pauseAnimations();}else{svg.unpauseAnimations();}label.textContent=paused?"resume (a)":"pause (a)";}'
         'function restart(){svg.setCurrentTime(0);if(paused){svg.pauseAnimations();}else{svg.unpauseAnimations();}}'
         'document.getElementById("ctl").addEventListener("click",toggle);'
         'document.getElementById("ctl-restart").addEventListener("click",restart);'
         'document.addEventListener("keydown",function(e){if(e.key==="a"){toggle();}else if(e.key==="r"){restart();}});})();'
         '</script>')
o.append("</svg>")
svg = "\n".join(o) + "\n"

here = pathlib.Path(__file__).resolve().parent
(here / "pool-exhaustion.svg").write_text(svg)
deck = here.parent / "deck" / "slides.md"
md = deck.read_text()
inline = svg.replace(f'width="{W}" height="{H}"', 'width="1150" height="470"', 1).rstrip("\n")
block = "<!-- pool-exhaustion:begin (generated by charts/make_pool_exhaustion.py; do not edit by hand) -->\n" + inline + "\n<!-- pool-exhaustion:end -->"
if "<!-- pool-exhaustion:begin" not in md:
    raise SystemExit("slides.md has no pool-exhaustion markers")
md = re.sub(r"<!-- pool-exhaustion:begin.*?<!-- pool-exhaustion:end -->", lambda m: block, md, flags=re.S)
deck.write_text(md)
print(f"wrote pool-exhaustion.svg and the inline copy: period {P}s, slow at {t_slow:.1f}s, exhausted at {t_exhausted:.1f}s, recovers at {t_recover:.1f}s, {len(anims)} animations")
