#!/usr/bin/env python3
"""Keep the per-slide markers in slides.md in step with the rendered slide order.

Every slide carries one line, placed right after its `---` separator and any
`<!-- _directive: ... -->` lines:

    [//]: # (slide N · short-id)

It is a markdown link-reference definition, so Marp renders nothing for it and it is
not an HTML comment, so it never becomes a speaker note. short-id is stable: once
written it is never changed by this script. Only N is rewritten, to the slide's
position in the deck (1 = the first slide after the front matter).

A slide without a marker gets one, with an id made from its first heading, else its
first image file name, else "slide-N", made unique with a numeric suffix.

After the marker it keeps a `<div class="devtag">TAG</div>` line (see TAGS below).
Idempotent: running it twice changes nothing the second time.
Usage: renumber.py [slides.md]      (run from deck/ before marp)
"""
import re
import sys

MARKER = re.compile(r"^\[//\]: # \(slide (\d+) · ([a-z0-9][a-z0-9-]*)\)$")
DEVTAG = re.compile(r'^<div class="devtag">[A-Z0-9]+</div>$')
# Development tags (2026-11-18): a short upper-case noun per slide, rendered small next to the page
# number so Scott can name slides while the deck is being edited. Hidden for the real deck by the
# commented-out rule in pgslides.css. An id not listed here gets its first five letters upper-cased.
TAGS = {
    "title": "TITLE", "premise": "PREM", "section-mistakes": "SECT", "symptoms": "CONN",
    "connection-storms": "STORM", "connection-storm-chart": "CHART", "connection-pooled-chart": "CHRT2", "connection-storm-chart-pgbouncer": "BOUNC",
    "pool-code": "POOLC", "connection-storms-detection": "DETEC", "pool-fix": "FIX",
    "mvcc-primer": "PRIME", "mvcc-bloat": "BLOAT", "mvcc-json": "JSON", "mvcc-json-year": "JYEAR",
    "mvcc-year": "YEAR", "mvcc-year-again": "YEAR2", "mvcc-connections": "MCONN", "mvcc-connections-anim": "MANIM", "mvcc-fix": "MFIX", "mvcc-fix-better": "MFIX2",
    "open-txn": "OPEN", "open-txn-again": "OPEN2", "xmin-horizon": "XMIN", "vacuum-holdback": "VACHB", "holders-table": "HOLDR", "vacuum-log": "VLOG",
    "open-txn-detection": "ODET", "open-txn-fix": "OFIX", "open-txn-fix-server": "OFIXS", "open-txn-connections": "OCONN", "open-txn-connections-fixed": "OCON2",
    "bulk-delete": "BULK", "bulk-delete-detection": "BDET", "page-diagram": "PAGE", "partition-fix": "PART", "bulk-delete-connections": "BCONN",
    "unused-indexes": "INDEX", "index-writes": "IWRIT", "unused-indexes-detection": "IDET",
    "hot-table": "HOT", "hot-index-chart": "HOTCH", "hot-ratio": "RATIO",
    "catalog": "CATLG", "efficiency": "EFFIC", "wednesday": "WEDS", "questions": "QUEST",
    "appendix-index-thinning": "THIN", "defaults": "DFLT",
}


def devtag(sid):
    return TAGS.get(sid) or re.sub(r"[^a-z0-9]", "", sid)[:5].upper()


def with_devtag(body):
    """Make the line after the marker the slide's dev tag, followed by a blank line. Idempotent."""
    idx = next((k for k, line in enumerate(body) if MARKER.match(line)), None)
    if idx is None:
        return body
    tag = f'<div class="devtag">{devtag(MARKER.match(body[idx]).group(2))}</div>'
    if idx + 1 < len(body) and DEVTAG.match(body[idx + 1]):
        body = body[:idx + 1] + [tag] + body[idx + 2:]
    else:
        body = body[:idx + 1] + [tag] + body[idx + 1:]
    if idx + 2 >= len(body) or body[idx + 2].strip() != "":
        body = body[:idx + 2] + [""] + body[idx + 2:]
    return body
DIRECTIVE = re.compile(r"^<!--\s*_\w+\s*:.*-->$")
FENCE = re.compile(r"^(```|~~~)")


def kebab(text):
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"[`*_#]", "", text).lower()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return "-".join(text.split("-")[:5]) or ""


def split_slides(lines):
    """Return (front_matter_lines, [slide_lines, ...]); separators are dropped."""
    front, i = [], 0
    if lines and lines[0] == "---":
        j = lines.index("---", 1)
        front, i = lines[: j + 1], j + 1
    slides, cur, in_fence = [], [], False
    for line in lines[i:]:
        if FENCE.match(line):
            in_fence = not in_fence
        if line == "---" and not in_fence:
            slides.append(cur)
            cur = []
        else:
            cur.append(line)
    slides.append(cur)
    return front, slides


def guess_id(body, n):
    for line in body:
        m = re.match(r"^#{1,6}\s+(.*)", line)
        if m and kebab(m.group(1)):
            return kebab(m.group(1))
    for line in body:
        m = re.search(r"!\[[^\]]*\]\(([^)]+)\)", line)
        if m:
            return kebab(m.group(1).rsplit("/", 1)[-1].rsplit(".", 1)[0])
    return f"slide-{n}"


def process(text):
    trailing_nl = text.endswith("\n")
    lines = text.split("\n")
    if trailing_nl:
        lines = lines[:-1]
    front, slides = split_slides(lines)

    used = set()
    for body in slides:
        for line in body:
            m = MARKER.match(line)
            if m:
                used.add(m.group(2))

    out_slides = []
    for n, body in enumerate(slides, start=1):
        idx = next((k for k, line in enumerate(body) if MARKER.match(line)), None)
        if idx is not None:
            sid = MARKER.match(body[idx]).group(2)
            body = body[:idx] + [f"[//]: # (slide {n} · {sid})"] + body[idx + 1:]
        else:
            base = guess_id(body, n)
            sid, k = base, 2
            while sid in used:
                sid, k = f"{base}-{k}", k + 1
            used.add(sid)
            # insert after leading blank lines and directive comments
            pos = 0
            last_directive = -1
            while pos < len(body) and (body[pos].strip() == "" or DIRECTIVE.match(body[pos].strip())):
                if body[pos].strip():
                    last_directive = pos
                pos += 1
            at = last_directive + 1
            new = [f"[//]: # (slide {n} · {sid})"]
            if at == 0 or body[0].strip() != "":
                new = ([""] if at == 0 else []) + new
            if at < len(body) and body[at].strip() != "":
                new = new + [""]
            body = body[:at] + new + body[at:]
        out_slides.append(with_devtag(body))

    out = list(front)
    for k, body in enumerate(out_slides):
        if k:
            out.append("---")
        out.extend(body)
    result = "\n".join(out)
    return result + ("\n" if trailing_nl else "")


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "slides.md"
    text = open(path, encoding="utf-8").read()
    new = process(text)
    if new != text:
        open(path, "w", encoding="utf-8").write(new)
        print(f"renumber: updated {path}")
    else:
        print(f"renumber: {path} already current")
    for line in new.split("\n"):
        m = MARKER.match(line)
        if m:
            print(f"  {int(m.group(1)):>2}  {m.group(2)}")


if __name__ == "__main__":
    main()
