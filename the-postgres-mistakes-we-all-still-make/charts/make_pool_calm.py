"""Render charts/pool-calm.svg and inline it into deck/slides.md between the pool-calm markers.

The OCONN animation (make_pool_exhaustion.py) after the fix (2026-11-18). Same geometry and style. Autocommit is on and the
charge runs with no transaction open, so when the payments API slows down and then goes down, requests wait on HTTP and
nothing in Postgres is held: five server connections, all free, the database idle. The API recovers, the waiting requests
run their UPDATE, nothing to clean up. Ids are prefixed pc so the two animations can share one HTML page.

Run: python3 -I make_pool_calm.py   (any cwd; build.sh runs it before renumber)
"""
import pathlib, re

INK, INK2, MUTED, SURF, AXIS = "#f0efec", "#c3c2b7", "#898781", "#1a1a19", "#383835"
S1, S2, S3, AMBER, RED = "#3987e5", "#d95926", "#199e70", "#e0a52a", "#e5484d"
W, H = 1100, 450
HOLD = 2.0
START = 5
APP_Y = (70, 150, 230)

# ---- timeline
BLIPS = [(1, HOLD + 0.8, HOLD + 1.1), (3, HOLD + 1.9, HOLD + 2.2), (0, HOLD + 3.0, HOLD + 3.3), (2, HOLD + 3.1, HOLD + 3.4)]
t_slow = HOLD + 4.6
t_down = t_slow + 2.5
WAITS = [(k, t_slow + 0.4 * n) for n, k in enumerate([0, 1, 2, 3, 4, 5, 6, 7, 8])]   # requests waiting on HTTP, one per call path
t_recover = t_down + 5.0
P = round(t_recover + 3.0, 1)

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

o = [f'<svg xmlns="http://www.w3.org/2000/svg" id="pool-calm-svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="DejaVu Sans, system-ui, sans-serif">',
     f'<rect width="{W}" height="{H}" fill="{SURF}"/>']
ids = {}
def uid(prefix):
    ids[prefix] = ids.get(prefix, 0) + 1
    return f"pc-{prefix}{ids[prefix]}"
def text(x, y, s, size=14, fill=INK, anchor="start", id=None, opacity=None):
    i = f' id="{id}"' if id else ""; op = f' opacity="{opacity}"' if opacity is not None else ""
    o.append(f'<text{i} x="{x}" y="{y}" fill="{fill}" font-size="{size}" text-anchor="{anchor}"{op}>{s}</text>')
def rect(x, y, w, h, color, op=0.14, rx=8, id=None, sw=1.5, stroke=None, opacity=None):
    i = f' id="{id}"' if id else ""; vis = f' opacity="{opacity}"' if opacity is not None else ""
    o.append(f'<rect{i} x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{color}" fill-opacity="{op}" stroke="{stroke or color}" stroke-width="{sw}"{vis}/>')

# ---- geometry (same as make_pool_exhaustion.py)
PX, PY, PW, PH = 380, 44, 460, 340
AX, AW = 110, 150
APX = 20
API_Y = 318
APPS = len(APP_Y)
MAXC = 20
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

# ---- payments API: green, slow, down, green again
rect(APX, API_Y, AW, 56, S3, id="pc-api")
sched("pc-api", "fill", [(0, S3), (t_slow, AMBER), (t_down, RED), (t_recover, S3)])
sched("pc-api", "stroke", [(0, S3), (t_slow, AMBER), (t_down, RED), (t_recover, S3)])
text(APX + AW / 2, API_Y + 24, "payments API", 14, anchor="middle")
text(APX + AW / 2, API_Y + 43, "response: 50 ms", 12, S3, "middle", id="pc-rt-ok"); sched("pc-rt-ok", "opacity", [(0, 1), (t_slow, 0), (t_recover, 1)])
text(APX + AW / 2, API_Y + 43, "response: 2 s", 12, AMBER, "middle", id="pc-rt-slow", opacity=0); sched("pc-rt-slow", "opacity", [(0, 0), (t_slow, 1), (t_down, 0)])
text(APX + AW / 2, API_Y + 43, "down", 12, RED, "middle", id="pc-rt-down", opacity=0); sched("pc-rt-down", "opacity", [(0, 0), (t_down, 1), (t_recover, 0)])

# ---- the five server connections: always green, always free
for k in range(START):
    ya, yb = line_ends(k)
    o.append(f'<line x1="{AX + AW}" y1="{ya:.0f}" x2="{PX}" y2="{yb:.0f}" stroke="{S3}" stroke-width="1.3"/>')

# ---- requests waiting on HTTP: amber dashed calls that pile up at the API and clear on recovery
for k, ta in WAITS:
    pid = uid("call"); o.append(f'<path id="{pid}" d="{call_path(k)}" fill="none" stroke="{AMBER}" stroke-width="1.2" stroke-dasharray="4 3" opacity="0"/>')
    sched(pid, "opacity", [(0, 0), (ta, 1), (t_recover, 0)])
wl = uid("wait"); text(AX + AW / 2, APP_Y[-1] + 78, "threads waiting on HTTP, no transaction open", 11.5, AMBER, "middle", id=wl, opacity=0)
sched(wl, "opacity", [(0, 0), (t_slow + 0.4, 1), (t_recover, 0)])

# ---- the database
o.append(f'<path d="M {PX},{top} V {bot} A {RX},{RY} 0 0 0 {PX+PW},{bot} V {top}" fill="{S3}" fill-opacity="0.08" stroke="{S3}" stroke-width="1.5"/>')
o.append(f'<ellipse cx="{cxp}" cy="{top}" rx="{RX}" ry="{RY}" fill="{S3}" fill-opacity="0.22" stroke="{S3}" stroke-width="1.5"/>')
text(cxp, top + 44, f"Postgres: {START} server connections, all free", 15, anchor="middle")
for k in range(START):
    x, y = slot_xy(k)
    rect(x, y, SW, SH, S3, op=0.8, rx=6)
idl = uid("idle"); text(cxp, SY + SH + 70, "idle", 26, MUTED, "middle", id=idl, opacity=0); sched(idl, "opacity", [(0, 0), (t_slow, 1), (t_recover, 0)])
text(PX + 30, bot - 10, "green: free", 12, S3)

# ---- healthy-phase blips: a connection runs the UPDATE for a moment
for k, ta, tb in BLIPS:
    x, y = slot_xy(k)
    bs = uid("bslot"); rect(x, y, SW, SH, S1, op=0.8, rx=6, id=bs, opacity=0); sched(bs, "opacity", [(0, 0), (ta, 1), (tb, 0)])
    bl = uid("blab"); text(x + SW / 2, y + SH / 2 + 4, "UPDATE", 10, anchor="middle", id=bl, opacity=0); sched(bl, "opacity", [(0, 0), (ta, 1), (tb, 0)])

# ---- captions
caps = [("autocommit on. A request charges first, with no transaction open, then runs one UPDATE in a few milliseconds", (HOLD, t_slow)),
        ("the payments API slows down. Requests wait on HTTP. No transaction is open, so no server connection is held", (t_slow, t_down)),
        ("the payments API is down. Every request is waiting on HTTP. Postgres has five free connections and nothing to do", (t_down, t_recover))]
for s, (a, b) in caps:
    cid = uid("cap"); text(20, H - 12, s, 15, id=cid, opacity=0); sched(cid, "opacity", [(0, 0), (a, 1), (b, 0)])
cid = uid("cap"); text(20, H - 12, "the payments API recovers. The waiting requests run their UPDATE and finish. Nothing to clean up", 15, id=cid)
sched(cid, "opacity", [(0, 1), (HOLD, 0), (t_recover, 1)])

# ---- controls (inline HTML deck only). Same keys as the OCONN animation; both toggle together, like the primer's shared "a"
rect(W - 96, 10, 86, 28, SURF, op=1, rx=6, sw=1.2, stroke=AXIS)
text(W - 53, 29, "pause (a)", 13, INK2, "middle", id="pc-ctl-label")
rect(W - 192, 10, 86, 28, SURF, op=1, rx=6, sw=1.2, stroke=AXIS)
text(W - 149, 29, "restart (r)", 13, INK2, "middle")
o += anims
o.append(f'<rect id="pc-ctl" x="{W - 96}" y="10" width="86" height="28" rx="6" fill="transparent" cursor="pointer"/>')
o.append(f'<rect id="pc-ctl-restart" x="{W - 192}" y="10" width="86" height="28" rx="6" fill="transparent" cursor="pointer"/>')
o.append('<script>'
         '(function(){var svg=document.getElementById("pool-calm-svg");if(!svg||!svg.pauseAnimations)return;'
         'var paused=false,label=document.getElementById("pc-ctl-label");'
         'function toggle(){paused=!paused;if(paused){svg.pauseAnimations();}else{svg.unpauseAnimations();}label.textContent=paused?"resume (a)":"pause (a)";}'
         'function restart(){svg.setCurrentTime(0);if(paused){svg.pauseAnimations();}else{svg.unpauseAnimations();}}'
         'document.getElementById("pc-ctl").addEventListener("click",toggle);'
         'document.getElementById("pc-ctl-restart").addEventListener("click",restart);'
         'document.addEventListener("keydown",function(e){if(e.key==="a"){toggle();}else if(e.key==="r"){restart();}});})();'
         '</script>')
o.append("</svg>")
svg = "\n".join(o) + "\n"

here = pathlib.Path(__file__).resolve().parent
(here / "pool-calm.svg").write_text(svg)
deck = here.parent / "deck" / "slides.md"
md = deck.read_text()
inline = svg.replace(f'width="{W}" height="{H}"', 'width="1150" height="470"', 1).rstrip("\n")
block = "<!-- pool-calm:begin (generated by charts/make_pool_calm.py; do not edit by hand) -->\n" + inline + "\n<!-- pool-calm:end -->"
if "<!-- pool-calm:begin" not in md:
    raise SystemExit("slides.md has no pool-calm markers")
md = re.sub(r"<!-- pool-calm:begin.*?<!-- pool-calm:end -->", lambda m: block, md, flags=re.S)
deck.write_text(md)
print(f"wrote pool-calm.svg and the inline copy: period {P}s, slow at {t_slow:.1f}s, down at {t_down:.1f}s, recovers at {t_recover:.1f}s, {len(anims)} animations")
