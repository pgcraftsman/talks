"""Render charts/mvcc-year.svg and charts/mvcc-year-xmin.svg in the heap-page style of the MVCC primer.

"year"  one user's row after a year of daily logins with no VACUUM. Sizes from pg_column_size() on local
        PG 17.10, 2026-11-17: the profile jsonb is 656 bytes with 5 logins and grows 24 bytes per appended
        timestamp; 9,296 bytes at 365. Tuple = 24 header + 8 id + jsonb.
"xmin"  the repeat slide after the vacuum-holdback chart (2026-11-18): one checkout whose payment-gateway call never
        returned sits idle in transaction over a weekend (48 hours) and pins the xmin horizon at xid 501 while a million users
        UPDATE last_login once an hour. Every version 110 bytes. Per user 49 versions, 48 dead, none removable; 48 million
        dead versions and 5.3 GB database-wide.
Static, no animation.
"""
import pathlib

INK, INK2, MUTED, SURF, AXIS = "#f0efec", "#c3c2b7", "#898781", "#1a1a19", "#383835"
S1, S2, S3, AMBER, RED = "#3987e5", "#d95926", "#199e70", "#e0a52a", "#e5484d"
W, H = 1100, 430


def size_at(n):            # tuple bytes with n logins in login_history
    return 24 + 8 + 656 + 24 * (n - 5)


def render(variant):
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="DejaVu Sans, system-ui, sans-serif">',
         f'<rect width="{W}" height="{H}" fill="{SURF}"/>']

    def text(x, y, s, size=14, fill=INK, anchor="start", mono=False):
        ff = ' font-family="DejaVu Sans Mono, Menlo, monospace"' if mono else ""
        o.append(f'<text x="{x}" y="{y}" fill="{fill}" font-size="{size}" text-anchor="{anchor}"{ff}>{s}</text>')

    def rect(x, y, w, h, color, op=0.14, rx=8, sw=1.5, dash=None):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        o.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{color}" fill-opacity="{op}" stroke="{color}" stroke-width="{sw}"{d}/>')

    def line(x1, y1, x2, y2, color, sw=1.2, dash=None):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        o.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="{sw}"{d}/>')

    if variant == "year":
        N = 365
        total_dead = sum(size_at(n) for n in range(1, N))      # versions 1..364 are dead
        live = size_at(N)
        title = "users, Jane's row, one login a day"
        rows = [("500", "502", "1", '{"name": "Jane Smith", ...}', 110, "dead"),
                ("502", "610", "1", '{..., "login_history": [1 login]}', size_at(1), "dead"),
                ("610", "731", "1", '{..., "login_history": [2 logins]}', size_at(2), "dead"),
                ("731", "858", "1", '{..., "login_history": [3 logins]}', size_at(3), "dead"),
                (None, None, None, "361 more versions, each 24 bytes bigger than the last", None, ""),
                ("46,210", "", "1", '{..., "login_history": [365 logins]}', live, "live")]
        dead_label = "dead until VACUUM"
        n_dead = N - 1
    else:
        HOURS, USERS = 48, 1_000_000          # one checkout stuck on the payment gateway over a weekend
        N = HOURS + 1                          # 48 hourly updates plus the original row
        V = 110
        total_dead = (N - 1) * V
        live = V
        db_updates = USERS * HOURS             # 48,000,000 commits behind the horizon
        step = db_updates // (N - 1)           # about a million xids between Jane's versions
        x = [502, 502 + step + 15, 502 + 2 * step + 31, 502 + 3 * step + 46]   # 502, 1,000,517, 2,000,533, 3,000,548
        title = "users, Jane's row, last_login updated once an hour"
        rows = [("500", "502", "1", '{"name": "Jane Smith", ...}', V, "dead"),
                (f"{x[0]:,}", f"{x[1]:,}", "1", '{..., "last_login": "Sat 00:00"}', V, "dead"),
                (f"{x[1]:,}", f"{x[2]:,}", "1", '{..., "last_login": "Sat 01:00"}', V, "dead"),
                (f"{x[2]:,}", f"{x[3]:,}", "1", '{..., "last_login": "Sat 02:00"}', V, "dead"),
                (None, None, None, f"{N - 5} more versions, {V} bytes each, a million xids apart", None, ""),
                (f"{502 + db_updates + 109:,}", "", "1", '{..., "last_login": "Sun 23:00"}', live, "live")]
        dead_label = "dead, cannot be vacuumed"
        n_dead = N - 1
    pages = -(-(total_dead + live) // 8192)

    # ---- the heap, drawn as one tall page for the story
    HX, HY, HW = 24, 10, 700
    HH = 314 if variant == "xmin" else 300    # the xmin variant has a 14 px gap for the horizon line
    rect(HX, HY, HW, HH, S3, op=0.07)
    text(HX + 14, HY + 24, title, 15, INK)
    text(HX + HW - 14, HY + 24, f"{pages} page" + ("s" if pages != 1 else ""), 12.5, MUTED, "end")
    # the xmin variant's state label is longer, so its column sits left of the heap edge
    state_x, state_fs, strike_end = (HX + 530, 10.5, HX + 524) if variant == "xmin" else (HX + 590, 11.5, HX + 560)
    # the xmin variant's xids run to eight digits: smaller xid font and the columns from id onward shifted 16 px right
    xid_fs, sh = (12, 16) if variant == "xmin" else (13, 0)
    COL = {"xmin": HX + 18, "xmax": HX + 96, "id": HX + 172 + sh, "profile": HX + 214 + sh, "size": HX + 500 + sh, "state": state_x + sh}
    for k, lab in [("xmin", "xmin"), ("xmax", "xmax"), ("id", "id"), ("profile", "profile"), ("size", "bytes"), ("state", "")]:
        text(COL[k], HY + 50, lab, 12, MUTED, mono=True)
    line(HX + 10, HY + 60, HX + HW - 10, HY + 60, AXIS, 1)
    y = HY + 86
    for i, (xmin, xmax, id_, prof, sz, st) in enumerate(rows):
        rect(HX + 8, y - 20, HW - 16, 28, INK, op=0.04, rx=4, sw=0)
        if xmin is None:
            text(COL["xmin"], y, prof, 12, MUTED)
        else:
            dead = st == "dead"; fill = MUTED if dead else INK
            text(COL["xmin"], y, xmin, xid_fs, fill, mono=True); text(COL["xmax"], y, xmax, xid_fs, fill, mono=True)
            text(COL["id"], y, id_, 13, fill, mono=True); text(COL["profile"], y, prof, 12.5, fill, mono=True)
            text(COL["size"], y, f"{sz:,}", 13, fill, mono=True)
            text(COL["state"], y, dead_label if dead else "live", state_fs, MUTED if dead else S3)
            if dead:
                line(HX + 165 + sh, y - 5, strike_end + sh, y - 5, RED, 1.4)
        if variant == "xmin" and i == 0:
            # the horizon sits in the gap between row 1 and row 2: everything below it has xmax newer than the idle session's xid
            line(HX + 10, y + 13, HX + HW - 10, y + 13, RED, 1.2, dash="5,4")
            text(COL["profile"], y + 24, "xmin horizon = 501, one checkout stuck on the gateway for 48 hours, since Fri 23:00", 11, RED)
            y += 14
        y += 34
    per_user = f"{(total_dead + live) / 1e6:.1f} MB" if variant == "year" else f"{(total_dead + live) / 1e3:.1f} KB"
    text(HX + 14, HY + HH - 14, f"one live row, {n_dead:,} dead versions, {per_user}. A reader of this row steps over all of it", 12.5, MUTED)

    # ---- the free space map
    FY, FH = HY + HH + 12, 86
    rect(HX, FY, HW, FH, S1, op=0.07)
    if variant == "year":
        # with VACUUM, every freed version is smaller than the next one
        text(HX + 14, FY + 22, "with autovacuum keeping up, the free space map after each UPDATE", 13, INK)
        text(HX + 14, FY + 44, f"version 2 freed {size_at(1)} bytes. Version 3 needs {size_at(2)}. It does not fit, and neither does any version after it", 12, INK2)
        text(HX + 14, FY + 64, "a document that only grows never fits the space its last version freed", 12, S1)
    else:
        text(HX + 14, FY + 22, "the free space map never gets an entry", 13, INK)
        text(HX + 14, FY + 44, f"autovacuum ran all weekend. Cutoff 501 every time, {db_updates // 1_000_000} million commits behind, nothing removed", 12, INK2)
        text(HX + 14, FY + 64, "with vacuum unable to progress past an old xid, these rows have no chance of being reused", 12, S1)

    # ---- the arithmetic at scale, right side
    RX = HX + HW + 30
    text(RX, HY + 24, "arithmetic from the measured sizes", 13, INK2)
    if variant == "year":
        items = [("one user, one year", f"{(total_dead + live) / 1e6:.1f} MB, {pages} pages"),
                 ("one million users", f"{(total_dead + live) * 1e6 / 1e12:.1f} TB of versions"),
                 ("live data in it", f"{live * 1e6 / 1e9:.1f} GB"),
                 ("bloat, dead versions", f"{total_dead * 1e6 / 1e12:.2f} TB ({total_dead:,} bytes per user)", RED)]
        fix = ["login_history is a table,", "not a key in the document.", "INSERT 24 bytes, UPDATE nothing"]
    else:
        items = [("one user, one weekend", f"{per_user}, {pages} page"),
                 ("one million users", f"{(total_dead + live) * USERS / 1e9:.1f} GB of versions"),
                 ("live data in it", f"{round(live * USERS / 1e6)} MB"),
                 ("bloat, dead versions", f"{total_dead * USERS / 1e9:.1f} GB ({total_dead:,} bytes per user)", RED)]
        fix = ["COMMIT or kill the stuck session.", "The next vacuum pass removes", f"{n_dead * USERS // 1_000_000} million versions"]
    y = HY + 50
    for item in items:
        k, v = item[0], item[1]; fill = item[2] if len(item) > 2 else INK
        text(RX, y, k, 12.5, MUTED); text(RX, y + 18, v, 14, fill); y += 42
    text(RX, y + 6, "the fix", 12.5, MUTED)
    for n, s_ in enumerate(fix):
        text(RX, y + 26 + n * 19, s_, 14, S3)
    o.append("</svg>")
    return "\n".join(o) + "\n", dict(dead=n_dead, mb=(total_dead + live) / 1e6, pages=pages, live=live, dead_bytes=total_dead)


here = pathlib.Path(__file__).resolve().parent
for variant, name in [("year", "mvcc-year.svg"), ("xmin", "mvcc-year-xmin.svg")]:
    svg, info = render(variant)
    (here / name).write_text(svg)
    print(f"wrote {name}: {info['dead']:,} dead versions, {info['mb']:.2f} MB, {info['pages']} pages, "
          f"live {info['live']} bytes, dead {info['dead_bytes']:,} bytes")
