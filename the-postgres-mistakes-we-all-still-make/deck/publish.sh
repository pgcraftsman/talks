#!/usr/bin/env bash
# Build a publishable copy of the deck into deck/public/: no speaker notes or other HTML comments, no dev tags,
# no demo file paths. The source slides.md keeps all of that for presenting. Run after build.sh.
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p public
python3 - <<'PY'
import re, pathlib
src = pathlib.Path("slides.md").read_text()
out = []
for line in src.split("\n"):
    if line.startswith("[//]: # (slide"):          # renumber markers
        continue
    if re.fullmatch(r'<div class="devtag">[A-Z0-9]+</div>', line.strip()):
        continue
    line = re.sub(r"\s+--\s*demos/\S+\s*$", "", line)   # trailing demo path on a SQL line
    line = re.sub(r"\s{2,}demos/\S+\s*$", "", line)     # demo path right-aligned in a SQL comment
    out.append(line)
text = "\n".join(out)
# drop every HTML comment except Marp directives (<!-- _class: ... -->) and the generated-block markers are comments too, so they go
text = re.sub(r"<!--(?!\s*_class:).*?-->", "", text, flags=re.S)
text = re.sub(r"\n{3,}", "\n\n", text)
text = text.replace("](../charts/", "](../../charts/")   # public/ is one level deeper than slides.md
pathlib.Path("public/slides.md").write_text(text)
print("public/slides.md:", text.count("<!--"), "directives kept,", len(re.findall(r"^---$", text, flags=re.M)), "separators")
PY
cp pgslides.css public/pgslides.css
MARP=./node_modules/.bin/marp
"$MARP" public/slides.md --theme-set public/pgslides.css --html --allow-local-files -o public/slides.html </dev/null
"$MARP" public/slides.md --theme-set public/pgslides.css --html --allow-local-files --pdf -o public/slides.pdf </dev/null
rm -f public/pgslides.css

# self-contained copy: every chart inlined as a data URI, so the file can be posted on its own
python3 - <<'PY'
import re, base64, pathlib, mimetypes
html = pathlib.Path("public/slides.html").read_text()
def inline(m):
    src = m.group(2)
    f = pathlib.Path("public") / src
    if not f.exists():
        return m.group(0)
    mime = mimetypes.guess_type(f.name)[0] or "application/octet-stream"
    return m.group(1) + f"data:{mime};base64," + base64.b64encode(f.read_bytes()).decode() + m.group(3)
out, n = re.subn(r'(<img[^>]*\ssrc=")(\.\./[^"]+)(")', inline, html)
pathlib.Path("public/slides-postable.html").write_text(out)
left = len(re.findall(r'src="\.\./', out))
print(f"public/slides-postable.html: {n} images inlined, {left} relative paths left")
PY
echo "public/slides.html and public/slides.pdf written"
