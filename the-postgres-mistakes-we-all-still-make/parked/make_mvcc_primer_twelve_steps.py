"""PARKED 2026-11-17: the twelve-step version of the MVCC primer, kept for audiences where it fits.

Steps 1 to 9 are the deck's primer plus Susie Rivera reusing Jane's freed 48 bytes (same size after
alignment padding). Steps 10 to 12: transaction 505 deletes Mike, VACUUM frees his 48 bytes, and
506 inserts a 64-byte Bartholomew Featherstonehaugh that does not fit, so the table grows a page.
Scott pulled it the same night: the DELETE has no real-world story except Mike's untimely demise,
which is not a thing to put in front of a mixed audience. The deck's nine-step version
(charts/make_mvcc_primer.py) drops Susie and the DELETE and has xid 7500 insert Bartholomew into
the gap VACUUM left behind Jane's old version.

Run: python3 -I parked/make_mvcc_primer_twelve_steps.py
Writes parked/mvcc-primer-twelve-steps.svg and parked/mvcc-end-state-twelve-steps.svg. It does not
touch deck/slides.md. To use it in a deck, point the inline markers at it the way build.sh does
for the nine-step generator.

Original docstring follows.
"""
"""Render charts/mvcc-primer.svg and inline it into deck/slides.md between markers.

Run: python3 -I make_mvcc_primer.py   (any cwd; build.sh runs it before renumber)

Story (Scott's whiteboard example, 101 level). A users table with id, first_name, last_name on one
heap page that is otherwise full. xid 500 bulk-loads Jane Smith and Mike Rivera and commits.
Transaction 501 opens and reads all users. Transaction 502 runs the marry-me UPDATE: Jane Smith
becomes Smith-Rivera. The page gets a second version of row 1 (56 bytes, the last of the page's
free space); the old version (48 bytes) gets xmax = 502. 501 reads again and still sees Smith,
because 502 has not committed. 502 commits; nothing on the page changes, and 501's next SELECT sees
Smith-Rivera (READ COMMITTED takes a new snapshot per statement). The old version is dead and
stays on the page until VACUUM. VACUUM frees its 48 bytes and the free space map records them; xid
504 inserts Susie Rivera, also 48 bytes after alignment padding, and the FSM sends her into that
space. Then the bloat case: 505 deletes Mike, VACUUM frees his 48 bytes, and 506 inserts
Bartholomew Featherstonehaugh, a 64-byte row. 48 is not enough, so the table grows a page and the
48 bytes on page 0 stay empty. (The ROLLBACK case was in an earlier version and came out on
2026-11-17: Scott narrates it.)

Byte counts: tuple header 24, id 8, each text 1-byte header + chars, data padded to 8.
Jane Smith 8+5+6=19 -> 24, Mike Rivera 8+5+7=20 -> 24, Susie Rivera 8+6+7=21 -> 24 (all 48 bytes);
Jane Smith-Rivera 8+5+13=26 -> 32 (56 bytes); Bartholomew Featherstonehaugh 8+12+18=38 -> 40 (64 bytes).

The HTML deck starts the animation paused on the first frame, with back / next / play controls
(keys b, n, a). Markup rules are the same as make_pool_exhaustion.py: SMIL with every attribute on
one period P, repeatCount indefinite, the end state held HOLD seconds at the top of each cycle,
shapes without children (Marp rewrites </rect>), every <animate> targets an id with href. Ids carry
an mv- prefix because the pool animation is inline in the same HTML document.
"""
import pathlib, re

INK, INK2, MUTED, SURF, AXIS = "#f0efec", "#c3c2b7", "#898781", "#1a1a19", "#383835"
S1, S2, S3, AMBER, RED = "#3987e5", "#d95926", "#199e70", "#e0a52a", "#e5484d"
W, H = 1100, 450
HOLD = 2.0

# ---- timeline (seconds)
t_load = HOLD                 # xid 500 inserts two rows and commits
t_r1 = t_load + 3.2           # 501 begins and reads
t_upd = t_r1 + 3.2            # 502 begins and updates
t_r2 = t_upd + 3.4            # 501 reads again, still sees Smith
t_commit = t_r2 + 3.2         # 502 commits
t_r3 = t_commit + 2.6         # 501 reads again, sees Smith-Rivera
t_dead = t_r3 + 2.8           # the old version is dead
t_vac = t_dead + 3.4          # VACUUM: the dead version becomes free space, the FSM records it
t_ins = t_vac + 3.2           # 504 inserts Susie Rivera into the freed space
t_del = t_ins + 3.4           # 505 deletes Mike and commits
t_vac2 = t_del + 3.2          # VACUUM frees Mike's 48 bytes
t_big = t_vac2 + 3.4          # 506 inserts a 64-byte row: does not fit, the table grows a page
t_end = t_big + 3.8
P = round(t_end, 1)

anims = []
SCHED = []            # (target, attr, steps) so a static frame can be baked
def sched(target, attr, steps):
    SCHED.append((target, attr, steps))
    vals, kts = [], []
    for n, (ts, v) in enumerate(steps):
        if n > 0:
            vals.append(steps[n - 1][1]); kts.append(max(0.0, ts - 0.05) / P)
        vals.append(v); kts.append(ts / P)
    vals.append(steps[-1][1]); kts.append(1.0)
    anims.append(f'<animate href="#{target}" attributeName="{attr}" values="{";".join(str(v) for v in vals)}" '
                 f'keyTimes="{";".join(f"{x:.4f}" for x in kts)}" calcMode="discrete" dur="{P}s" repeatCount="indefinite"/>')

o = [f'<svg xmlns="http://www.w3.org/2000/svg" id="mvcc-svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="DejaVu Sans, system-ui, sans-serif">',
     f'<rect width="{W}" height="{H}" fill="{SURF}"/>']
ids = {}
def uid(prefix):
    ids[prefix] = ids.get(prefix, 0) + 1
    return f"mv-{prefix}{ids[prefix]}"
def text(x, y, s, size=14, fill=INK, anchor="start", id=None, opacity=None, mono=False):
    i = f' id="{id}"' if id else ""; op = f' opacity="{opacity}"' if opacity is not None else ""
    ff = ' font-family="DejaVu Sans Mono, Menlo, monospace"' if mono else ""
    o.append(f'<text{i} x="{x}" y="{y}" fill="{fill}" font-size="{size}" text-anchor="{anchor}"{op}{ff}>{s}</text>')
def rect(x, y, w, h, color, op=0.14, rx=8, id=None, sw=1.5, stroke=None, opacity=None):
    i = f' id="{id}"' if id else ""; vis = f' opacity="{opacity}"' if opacity is not None else ""
    o.append(f'<rect{i} x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{color}" fill-opacity="{op}" stroke="{stroke or color}" stroke-width="{sw}"{vis}/>')
def line(x1, y1, x2, y2, color, sw=1.2, id=None, opacity=None):
    i = f' id="{id}"' if id else ""; vis = f' opacity="{opacity}"' if opacity is not None else ""
    o.append(f'<line{i} x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="{sw}"{vis}/>')
def show(target, windows):
    """visible during each (a, b) window, hidden otherwise; b=None means to the end of the period."""
    steps = [(0, 0)]
    for a, b in windows:
        if a == 0:
            steps[0] = (0, 1)
        else:
            steps.append((a, 1))
        if b is not None:
            steps.append((b, 0))
    sched(target, "opacity", steps)
def switch(x, y, steps, size=13, fill=INK, anchor="start", mono=True):
    """one text per distinct value; steps = [(t, value, fill?)], value "" shows nothing; each holds to the next step."""
    for n, st in enumerate(steps):
        t, v = st[0], st[1]; f = st[2] if len(st) > 2 else fill
        if v == "":
            continue
        tb = steps[n + 1][0] if n + 1 < len(steps) else None
        tid = uid("sw"); text(x, y, v, size, f, anchor, id=tid, opacity=0, mono=mono)
        show(tid, [(t, tb)])

# ---- geometry
HX, HY, HW, HH = 24, 40, 560, 250          # heap page 0
P1Y, P1H = HY + HH + 10, 46                 # heap page 1, appears at t_big
FY, FH = P1Y + P1H + 10, 60                 # the free space map
TX, TW = 610, 470                           # the two transaction panels
T1Y, T2Y, TH = 40, 190, 130
COLX = {"xmin": HX + 18, "xmax": HX + 88, "id": HX + 158, "first": HX + 200, "last": HX + 300, "state": HX + 424}
ROWY = [HY + 100, HY + 136, HY + 172]       # slot 1 (row 1 v1, later Susie), slot 2 (Mike), slot 3 (row 1 v2)
RH = 30

# ---- heap page 0
rect(HX, HY, HW, HH, S3, op=0.07)
text(HX + 14, HY + 24, "users, heap page 0", 15, INK)
switch(HX + HW - 14, HY + 24, [(0, "8,192 bytes, 48 free", MUTED), (t_load, "8,192 bytes, 56 free", INK2), (t_upd, "8,192 bytes, 0 free", INK2),
                                (t_vac, "8,192 bytes, 48 free", S1), (t_ins, "8,192 bytes, 0 free", INK2), (t_vac2, "8,192 bytes, 48 free", S1), (t_big, "8,192 bytes, 48 free", MUTED)],
       size=12.5, anchor="end", mono=False)
text(HX + 14, HY + 44, "xmin is the xid that wrote the version. xmax is the xid that deleted or replaced it", 11.5, INK2)
for k, lab in [("xmin", "xmin"), ("xmax", "xmax"), ("id", "id"), ("first", "first_name"), ("last", "last_name")]:
    text(COLX[k], HY + 68, lab, 12, MUTED, mono=True)
line(HX + 10, HY + 78, HX + HW - 10, HY + 78, AXIS, 1)
rect(HX + 8, ROWY[2] + 14, HW - 16, 26, INK, op=0.03, rx=4, sw=0)
text(HX + 18, ROWY[2] + 32, "and the other 150 rows on this page", 11.5, MUTED)

def row(y, xmin_steps, xmax_steps, id_, first, last_steps, windows, state_steps, strike_windows):
    """one row version. windows: when the row exists at all; strike_windows: when it is dead."""
    bg = uid("rowbg"); rect(HX + 8, y - 21, HW - 16, RH, INK, op=0.04, rx=4, id=bg, sw=0); show(bg, windows)
    switch(COLX["xmin"], y, xmin_steps)
    switch(COLX["xmax"], y, xmax_steps)
    tid = uid("rid"); text(COLX["id"], y, id_, 13, INK, id=tid, opacity=0, mono=True); show(tid, windows)
    tfn = uid("rfn"); text(COLX["first"], y, first, 13, INK, id=tfn, opacity=0, mono=True); show(tfn, windows)
    switch(COLX["last"], y, last_steps)
    switch(COLX["state"], y, state_steps, size=11.5, mono=False)
    sl = uid("strike"); line(HX + 150, y - 5, HX + 396, y - 5, RED, 1.6, id=sl, opacity=0); show(sl, strike_windows)
def free_slot(y, windows, label_steps):
    fs = uid("free"); o.append(f'<rect id="{fs}" x="{HX + 8}" y="{y - 21}" width="{HW - 16}" height="{RH}" rx="4" fill="none" stroke="{MUTED}" stroke-width="1" stroke-dasharray="5 4" opacity="0"/>'); show(fs, windows)
    switch(COLX["xmin"], y, label_steps, size=12, mono=False)

# slot 1: Jane Smith, written by 500. xmax 502 at the update, dead after the commit, freed by VACUUM.
# The hold at the top of the cycle shows the end state, so slot 1 holds Susie then.
row(ROWY[0],
    xmin_steps=[(0, ""), (t_load, "500"), (t_dead, "500", MUTED), (t_vac, "")],
    xmax_steps=[(0, ""), (t_upd, "502", AMBER), (t_commit, "502", INK), (t_dead, "502", MUTED), (t_vac, "")],
    id_="1", first="Jane",
    last_steps=[(0, ""), (t_load, "Smith"), (t_dead, "Smith", MUTED), (t_vac, "")],
    windows=[(t_load, t_vac)],
    state_steps=[(0, ""), (t_load, "48 bytes", MUTED), (t_upd, "xmax 502, in flight", AMBER), (t_commit, "old version", INK2), (t_dead, "dead until VACUUM", MUTED), (t_vac, "")],
    strike_windows=[(t_dead, t_vac)])
free_slot(ROWY[0], [(t_vac, t_ins)], [(0, ""), (t_vac, "free space, 48 bytes", S1), (t_ins, "")])
row(ROWY[0],
    xmin_steps=[(0, "504"), (t_load, ""), (t_ins, "504")], xmax_steps=[(0, "")], id_="3", first="Susie",
    last_steps=[(0, "Rivera"), (t_load, ""), (t_ins, "Rivera")], windows=[(0, t_load), (t_ins, None)],
    state_steps=[(0, "48 bytes, reused the space", S3), (t_load, ""), (t_ins, "48 bytes, reused the space", S3), (t_del, "48 bytes", MUTED)], strike_windows=[])
# slot 2: Mike Rivera, written by 500, deleted by 505, freed by VACUUM, and the space is never reused
row(ROWY[1],
    xmin_steps=[(0, ""), (t_load + 0.9, "500"), (t_del, "500", MUTED), (t_vac2, "")],
    xmax_steps=[(0, ""), (t_del, "505", MUTED), (t_vac2, "")],
    id_="2", first="Mike",
    last_steps=[(0, ""), (t_load + 0.9, "Rivera"), (t_del, "Rivera", MUTED), (t_vac2, "")],
    windows=[(t_load + 0.9, t_vac2)],
    state_steps=[(0, ""), (t_load + 0.9, "48 bytes", MUTED), (t_del, "dead, xmax 505", MUTED), (t_vac2, "")], strike_windows=[(t_del, t_vac2)])
free_slot(ROWY[1], [(0, t_load), (t_vac2, None)], [(0, "48 bytes free. Nothing coming is that small: bloat", MUTED), (t_load, ""), (t_vac2, "free space, 48 bytes", S1), (t_big, "48 bytes free. Nothing coming is that small: bloat", MUTED)])
# slot 3: Jane Smith-Rivera, written by 502, in flight, then committed and live
row(ROWY[2],
    xmin_steps=[(0, "502"), (t_load, ""), (t_upd, "502", AMBER), (t_commit, "502")],
    xmax_steps=[(0, "")],
    id_="1", first="Jane",
    last_steps=[(0, "Smith-Rivera"), (t_load, ""), (t_upd, "Smith-Rivera", AMBER), (t_commit, "Smith-Rivera")],
    windows=[(0, t_load), (t_upd, None)],
    state_steps=[(0, "56 bytes", MUTED), (t_load, ""), (t_upd, "56 bytes, in flight", AMBER), (t_commit, "56 bytes, live", S3), (t_vac, "56 bytes", MUTED)],
    strike_windows=[])

# page 0 footer: what the page holds
switch(HX + 14, HY + HH - 14, [(0, "48 bytes free that no row fits. The table grew a page instead", MUTED),
                               (t_load, "xid 500 wrote both rows and committed. 56 bytes left on the page", INK2),
                               (t_upd, "UPDATE wrote a second version of row 1 and set xmax on the first. Page full", INK2),
                               (t_commit, "COMMIT changed nothing on this page. It marked 502 committed in the clog", INK2),
                               (t_dead, "two live versions, one dead. Every reader steps over it until VACUUM", MUTED),
                               (t_vac, "VACUUM removed the dead version. 48 bytes free", INK2),
                               (t_ins, "the INSERT reused the 48 bytes. The table did not grow", INK2),
                               (t_del, "DELETE marked Mike's row dead. Its bytes are still taken", INK2),
                               (t_vac2, "VACUUM removed Mike's row. 48 bytes free", INK2),
                               (t_big, "48 bytes free that no row fits. The table grew a page instead", MUTED)],
       size=12.5, mono=False)

# ---- heap page 1, appended at t_big
p1 = uid("p1"); rect(HX, P1Y, HW, P1H, S2, op=0.07, id=p1, opacity=0); show(p1, [(0, t_load), (t_big, None)])
for s_, x_, y_, sz, fl, mono in [("users, heap page 1, new", HX + 14, P1Y + 18, 13, INK, False),
                                  ("506", COLX["xmin"], P1Y + 36, 13, INK, True), ("4", COLX["id"], P1Y + 36, 13, INK, True),
                                  ("Bartholomew", COLX["first"], P1Y + 36, 13, INK, True), ("Featherstonehaugh", COLX["last"] + 18, P1Y + 36, 13, INK, True)]:
    tid = uid("p1t"); text(x_, y_, s_, sz, fl, id=tid, opacity=0, mono=mono); show(tid, [(0, t_load), (t_big, None)])
tid = uid("p1t"); text(HX + HW - 14, P1Y + 18, "8,192 bytes, 8,128 free", 12.5, INK2, "end", id=tid, opacity=0); show(tid, [(0, t_load), (t_big, None)])
tid = uid("p1t"); text(HX + HW - 14, P1Y + 36, "64 bytes", 11.5, S2, "end", id=tid, opacity=0); show(tid, [(0, t_load), (t_big, None)])

# ---- the free space map, one entry per page, pointing at the freed space while there is some (101 version)
rect(HX, FY, HW, FH, S1, op=0.07)
text(HX + 14, FY + 18, "free space map (FSM), one entry per page", 13, INK)
switch(HX + 14, FY + 37, [(0, "page 0: 48 bytes free. Too small for any row that comes in", MUTED), (t_load, "page 0: 56 bytes free", INK2), (t_upd, "page 0: 0 bytes free", MUTED),
                          (t_vac, "page 0: 48 bytes free", S1), (t_ins, "page 0: 0 bytes free", MUTED), (t_vac2, "page 0: 48 bytes free", S1),
                          (t_big, "page 0: 48 bytes free. Too small for any row that comes in", MUTED)], size=12.5, mono=False)
switch(HX + 14, FY + 53, [(0, "page 1: 8,128 bytes free", S1), (t_load, ""), (t_big, "page 1: 8,128 bytes free", S1)], size=12.5, mono=False)
gx = HX + HW + 10
for y_, win in [(ROWY[0], (t_vac, t_ins)), (ROWY[1], (t_vac2, t_big))]:
    ar = uid("fsmarrow"); o.append(f'<path id="{ar}" d="M {HX + 230},{FY + 33} H {gx} V {y_ - 6} H {HX + HW + 2}" fill="none" stroke="{S1}" stroke-width="1.6" opacity="0"/>'); show(ar, [win])
    ah = uid("fsmhead"); o.append(f'<polygon id="{ah}" points="{HX + HW - 6},{y_ - 6} {HX + HW + 4},{y_ - 11} {HX + HW + 4},{y_ - 1}" fill="{S1}" opacity="0"/>'); show(ah, [win])

# ---- transaction panels
def panel(y, title, color):
    rect(TX, y, TW, TH, color, op=0.10)
    if title:
        text(TX + 14, y + 24, title, 14, color)
panel(T1Y, "transaction 501, the reader", S1)
panel(T2Y, "", S2)

# 501: BEGIN; SELECT * FROM users; results
text(TX + 14, T1Y + 48, "BEGIN;  SELECT * FROM users;", 12.5, INK, mono=True)
RY_ = [T1Y + 63, T1Y + 77, T1Y + 91, T1Y + 105]
switch(TX + 14, RY_[0], [(0, "1  Jane  Smith-Rivera", S1), (t_load, ""), (t_r1, "1  Jane  Smith", S1), (t_r3, "1  Jane  Smith-Rivera", S1)], size=12)
text(TX + 14, RY_[1], "2  Mike  Rivera", 12, S1, mono=True, id="mv-r2res", opacity=0); show("mv-r2res", [(t_r1, t_del)])
text(TX + 14, RY_[2], "3  Susie Rivera", 12, S1, mono=True, id="mv-r3res", opacity=0); show("mv-r3res", [(0, t_load), (t_ins, None)])
text(TX + 14, RY_[3], "4  Bartholomew  Featherstonehaugh", 12, S1, mono=True, id="mv-r4res", opacity=0); show("mv-r4res", [(0, t_load), (t_big, None)])
switch(TX + 14, T1Y + 123, [(0, "SELECT again. Three rows, one of them on a new page", S3),
                            (t_load, ""),
                            (t_r1, "snapshot: everything committed before now", INK2),
                            (t_r2, "SELECT again. Still Smith. 502 is in flight, its version is invisible", AMBER),
                            (t_r3, "SELECT again. Smith-Rivera. New statement, new snapshot", S3),
                            (t_ins, "SELECT again. Three rows. 504 committed", S3),
                            (t_del, "SELECT again. Two rows. 505 committed, Mike is gone", S3),
                            (t_big, "SELECT again. Three rows, one of them on a new page", S3)],
       size=11.5, mono=False)

# 502: BEGIN; UPDATE; COMMIT. Then the panel becomes VACUUM, 504, 505, VACUUM, 506.
switch(TX + 14, T2Y + 24, [(0, "transaction 506, a long name", S2), (t_load, "transaction 502, marry me", S2), (t_vac, "autovacuum, or VACUUM users", S3), (t_ins, "transaction 504, a new user", S2),
                           (t_del, "transaction 505, Mike leaves", S2), (t_vac2, "autovacuum, or VACUUM users", S3), (t_big, "transaction 506, a long name", S2)], size=14, mono=False)
switch(TX + 14, T2Y + 50, [(0, "BEGIN;"), (t_vac, "VACUUM users;"), (t_ins, "BEGIN;"), (t_vac2, "VACUUM users;"), (t_big, "BEGIN;")], size=12.5)
switch(TX + 14, T2Y + 70, [(0, "INSERT INTO users"), (t_load, "UPDATE users SET last_name = 'Smith-Rivera'"), (t_vac, "dead versions become free space on the page", INK2),
                           (t_ins, "INSERT INTO users VALUES (3, 'Susie', 'Rivera');"), (t_del, "DELETE FROM users WHERE id = 2;"),
                           (t_vac2, "dead versions become free space on the page", INK2), (t_big, "INSERT INTO users")], size=12.5)
switch(TX + 14, T2Y + 88, [(0, "  VALUES (4, 'Bartholomew', 'Featherstonehaugh');"), (t_load, "  WHERE id = 1;"), (t_vac, "the free space map (FSM) records how much", INK2), (t_ins, ""),
                           (t_vac2, "the free space map (FSM) records how much", INK2), (t_big, "  VALUES (4, 'Bartholomew', 'Featherstonehaugh');")], size=12.5)
switch(TX + 14, T2Y + 108, [(0, "COMMIT;", S3), (t_load, ""), (t_commit, "COMMIT;", S3), (t_vac, ""), (t_ins, "COMMIT;", S3), (t_del, "COMMIT;", S3), (t_vac2, ""), (t_big, "COMMIT;", S3)], size=12.5)
switch(TX + 14, T2Y + 124, [(0, "64 bytes. Page 0 has 48 free, so the table grows a page", RED), (t_load, ""), (t_upd, "in flight: holds xid 502 and a connection", AMBER), (t_commit, "committed", S3),
                             (t_vac, "no lock on the table, readers and writers carry on", INK2), (t_ins, "the FSM pointed at page 0, so Susie took the freed space", S3),
                             (t_del, "DELETE writes nothing new. It sets xmax, and the row is dead", INK2), (t_vac2, "48 bytes free on page 0 again", INK2),
                             (t_big, "64 bytes. Page 0 has 48 free, so the table grows a page", RED)], size=11.5, mono=False)
p1c = uid("p1cover"); rect(TX - 2, T1Y - 2, TW + 4, TH + 4, SURF, op=1, rx=8, id=p1c, sw=0); show(p1c, [(t_load, t_r1)])
p2c = uid("p2cover"); rect(TX - 2, T2Y - 2, TW + 4, TH + 4, SURF, op=1, rx=8, id=p2c, sw=0); show(p2c, [(t_load, t_upd)])

# ---- step title, top left
titles = [(0, "the whole story"), (t_load, "1. Bulk load"), (t_r1, "2. A reader takes a snapshot"), (t_upd, "3. UPDATE writes a new version"),
          (t_r2, "4. The reader still sees Smith"), (t_commit, "5. COMMIT"), (t_r3, "6. New statement, new snapshot"), (t_dead, "7. A dead version"),
          (t_vac, "8. VACUUM frees 48 bytes"), (t_ins, "9. The FSM reuses them"), (t_del, "10. DELETE"), (t_vac2, "11. VACUUM frees 48 bytes"), (t_big, "12. A row that does not fit")]
n_before = len(o); switch(HX, 30, titles, size=19, fill=INK, mono=False)
TITLE_IDS = [m for m in re.findall(r'id="(mv-sw\d+)"', "\n".join(o[n_before:]))]

# ---- caption
caps = [(0, "dead versions become free bytes. A row that fits reuses them; a row that does not grows the table and leaves the gap behind"),
        (t_load, "xid 500 bulk-loads the table in one transaction and commits. The page is otherwise full"),
        (t_r1, "501 reads. Its snapshot is everything committed before the statement started"),
        (t_upd, "502 updates row 1. Postgres never overwrites: a new version is written, and the old one gets xmax = 502"),
        (t_r2, "501 reads again and still sees Smith. 502 has not committed, so its version is invisible to everyone else"),
        (t_commit, "502 commits. The page does not change; the commit log now says 502 is committed"),
        (t_r3, "501's next statement takes a new snapshot and sees Smith-Rivera (READ COMMITTED, the default)"),
        (t_dead, "the old version is dead. It stays on the page until VACUUM, and every reader steps over it until then"),
        (t_vac, "VACUUM compacts the page, frees the dead version's 48 bytes, and records them in the free space map"),
        (t_ins, "504 inserts Susie Rivera, 48 bytes after padding. The FSM points at page 0, so she takes the freed space"),
        (t_del, "505 deletes Mike. DELETE writes nothing; it sets xmax, and once 505 commits the version is dead"),
        (t_vac2, "VACUUM frees Mike's 48 bytes and the FSM records page 0 again"),
        (t_big, "506 inserts a 64-byte row. 48 is not enough, so the table grows a page. The 48 bytes on page 0 stay empty: bloat")]
for n, (a, s) in enumerate(caps):
    b = caps[n + 1][0] if n + 1 < len(caps) else None
    cid = uid("cap"); text(20, H - 12, s, 14, id=cid, opacity=0); show(cid, [(a, b)])

# ---- static end state, used by the Mistake #1 opener slide: every opacity baked at t_big + 0.1, no controls
def value_at(steps, T):
    v = steps[0][1]
    for ts, val in steps:
        if T >= ts:
            v = val
    return v
T_STATIC = t_big + 0.1
static = "\n".join(o)
for target, attr, steps in SCHED:
    v = 0 if target in TITLE_IDS else value_at(steps, T_STATIC)
    static = re.sub(rf'(<[a-z]+ id="{re.escape(target)}"[^>]*?) opacity="[^"]*"', rf'\1 opacity="{v}"', static, count=1)
    if re.search(rf'<[a-z]+ id="{re.escape(target)}"[^>]*\sopacity=', static) is None:
        static = static.replace(f'id="{target}"', f'id="{target}" opacity="{v}"', 1)
static = static.replace('id="mvcc-svg"', 'id="mvcc-static"') + "\n</svg>\n"
(pathlib.Path(__file__).resolve().parent / "mvcc-end-state-twelve-steps.svg").write_text(static)

# ---- controls (inline HTML deck only): starts paused on the first frame; back / next step through the
# event times; play runs the SMIL clock; keys b, n and a do the same. Marp owns the arrow keys.
FRAMES = [t_load + 1.0, t_r1 + 0.1, t_upd + 0.1, t_r2 + 0.1, t_commit + 0.1, t_r3 + 0.1, t_dead + 0.1, t_vac + 0.1, t_ins + 0.1, t_del + 0.1, t_vac2 + 0.1, t_big + 0.1]
bx = W - 300
for n, (bid, lab) in enumerate([("mvcc-back", "back (b)"), ("mvcc-next", "next (n)"), ("mvcc-play", "play (a)")]):
    rect(bx + n * 96, 10, 88, 28, SURF, op=1, rx=6, sw=1.2, stroke=AXIS)
    text(bx + n * 96 + 44, 29, lab, 12.5, INK2, "middle", id=bid + "-label")
text(bx - 14, 29, f"step 1 of {len(FRAMES)}", 12.5, MUTED, "end", id="mvcc-step")
o += anims
for n, bid in enumerate(["mvcc-back", "mvcc-next", "mvcc-play"]):
    o.append(f'<rect id="{bid}" x="{bx + n * 96}" y="10" width="88" height="28" rx="6" fill="transparent" cursor="pointer"/>')
frames_js = ",".join(f"{f:.2f}" for f in FRAMES)
o.append('<script>'
         '(function(){var svg=document.getElementById("mvcc-svg");if(!svg||!svg.pauseAnimations)return;'
         f'var F=[{frames_js}],i=0,playing=false;'
         'var step=document.getElementById("mvcc-step"),play=document.getElementById("mvcc-play-label");'
         'function go(k){i=Math.max(0,Math.min(F.length-1,k));svg.setCurrentTime(F[i]);step.textContent="step "+(i+1)+" of "+F.length;}'
         'function pause(){playing=false;svg.pauseAnimations();play.textContent="play (a)";}'
         'function toggle(){if(playing){pause();}else{playing=true;svg.unpauseAnimations();play.textContent="pause (a)";}}'
         'function next(){if(playing)pause();go(i+1);} function back(){if(playing)pause();go(i-1);}'
         'svg.pauseAnimations();go(0);'
         'document.getElementById("mvcc-next").addEventListener("click",next);'
         'document.getElementById("mvcc-back").addEventListener("click",back);'
         'document.getElementById("mvcc-play").addEventListener("click",toggle);'
         'document.addEventListener("keydown",function(e){if(e.key==="n"){next();}else if(e.key==="b"){back();}else if(e.key==="a"){toggle();}});})();'
         '</script>')
o.append("</svg>")
svg = "\n".join(o) + "\n"

here = pathlib.Path(__file__).resolve().parent
(here / "mvcc-primer-twelve-steps.svg").write_text(svg)
print(f"wrote mvcc-primer-twelve-steps.svg and mvcc-end-state-twelve-steps.svg: period {P}s, {len(anims)} animations")
