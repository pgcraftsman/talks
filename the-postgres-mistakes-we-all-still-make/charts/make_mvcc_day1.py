"""Render charts/mvcc-day1.svg: the users(id, profile jsonb) table on day one, two rows on one heap page,
drawn in the same heap-page style as the MVCC primer. Sizes from pg_column_size() on local PG 17.10,
2026-11-17: Jane's jsonb 78 bytes, Mike's 79. Tuple = 24 header + 8 id + jsonb, so 110 and 111.
Static, no animation, no ids.
"""
import pathlib

INK, INK2, MUTED, SURF, AXIS = "#f0efec", "#c3c2b7", "#898781", "#1a1a19", "#383835"
S1, S2, S3, AMBER, RED = "#3987e5", "#d95926", "#199e70", "#e0a52a", "#e5484d"
W, H = 1100, 220
o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="DejaVu Sans, system-ui, sans-serif">',
     f'<rect width="{W}" height="{H}" fill="{SURF}"/>']
def text(x, y, s, size=14, fill=INK, anchor="start", mono=False):
    ff = ' font-family="DejaVu Sans Mono, Menlo, monospace"' if mono else ""
    o.append(f'<text x="{x}" y="{y}" fill="{fill}" font-size="{size}" text-anchor="{anchor}"{ff}>{s}</text>')
def rect(x, y, w, h, color, op=0.14, rx=8, sw=1.5):
    o.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{color}" fill-opacity="{op}" stroke="{color}" stroke-width="{sw}"/>')
def line(x1, y1, x2, y2, color, sw=1.2):
    o.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="{sw}"/>')

# ---- the heap page
HX, HY, HW, HH = 24, 10, 1052, 200
rect(HX, HY, HW, HH, S3, op=0.07)
text(HX + 14, HY + 26, "users, heap page 0", 15, INK)
text(HX + HW - 14, HY + 26, "8,192 bytes, two rows, 221 bytes used", 12.5, MUTED, "end")
COL = {"xmin": HX + 18, "xmax": HX + 96, "id": HX + 172, "profile": HX + 214, "size": HX + HW - 14}
for k, lab in [("xmin", "xmin"), ("xmax", "xmax"), ("id", "id"), ("profile", "profile")]:
    text(COL[k], HY + 56, lab, 12, MUTED, mono=True)
text(COL["size"], HY + 56, "bytes", 12, MUTED, "end", mono=True)
line(HX + 10, HY + 66, HX + HW - 10, HY + 66, AXIS, 1)
rows = [("500", "", "1", '{"id": 1, "name": "Jane Smith", "email": "jane@example.com"}', 110),
        ("500", "", "2", '{"id": 2, "name": "Mike Rivera", "email": "mike@example.com"}', 111)]
y = HY + 96
for xmin, xmax, id_, prof, sz in rows:
    rect(HX + 8, y - 21, HW - 16, 30, INK, op=0.04, rx=4, sw=0)
    text(COL["xmin"], y, xmin, 13, INK, mono=True); text(COL["xmax"], y, xmax, 13, INK, mono=True)
    text(COL["id"], y, id_, 13, INK, mono=True); text(COL["profile"], y, prof, 13, INK, mono=True)
    text(COL["size"], y, f"{sz}", 13, INK2, "end", mono=True)
    y += 38
text(HX + 14, HY + HH - 14, "xid 500 wrote both rows and committed. Each profile is one jsonb value, 78 and 79 bytes, plus a 32-byte tuple header and id", 12.5, INK2)
o.append("</svg>")
here = pathlib.Path(__file__).resolve().parent
(here / "mvcc-day1.svg").write_text("\n".join(o) + "\n")
print("wrote mvcc-day1.svg")
