"""Event banners in the NYC Postgres meetup house style (magenta, yellow triangle grid,
white title, speaker photo). Writes banner-1200x675.svg/.png (Meetup, LinkedIn, Reddit
link preview) and banner-1080x1080.svg/.png (LinkedIn and Facebook square posts).

    ../.venv/bin/python -I make_banners.py [path/to/headshot.jpg]

PNGs are rendered with headless Chrome (CHROME_PATH or the macOS / Linux default).
"""
import base64, io, os, subprocess, sys, tempfile
from PIL import Image, ImageEnhance

MAGENTA, YELLOW, WHITE = "#d34894", "#eac41d", "#ffffff"
FONT = "'Helvetica Neue', Helvetica, Arial, sans-serif"
TITLE = ["The Postgres Mistakes", "We All Still Make"]
SPEAKER, ROLE = "Scott Mead", "Senior Staff Engineer, Databricks"
WHEN = ["6 PM to 8 PM", "Wednesday, November 18, 2026"]
WHERE = ["Databricks Office", "5 Bryant Park, New York, NY 10018"]
HEADSHOT = sys.argv[1] if len(sys.argv) > 1 else "headshot.jpg"


def photo_data_uri(path, size=800):
    im = Image.open(path).convert("RGB")
    im = ImageEnhance.Contrast(im).enhance(1.18)
    im = ImageEnhance.Color(im).enhance(1.25)
    im = ImageEnhance.Brightness(im).enhance(1.04)
    im = im.resize((size, round(size * im.height / im.width)), Image.LANCZOS)
    buf = io.BytesIO(); im.save(buf, "JPEG", quality=88, optimize=True)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def triangles(x0, y0, cell, cols, rows):
    """Grid of squares split on the diagonal: yellow or white against the magenta background."""
    out = []
    accents = {(0, 1): WHITE, (2, 0): WHITE}          # (col,row) cells drawn white instead of yellow
    for r in range(rows):
        for c in range(cols):
            x, y = x0 + c * cell, y0 + r * cell
            col = accents.get((c, r), YELLOW)
            if (c + r) % 2 == 0:   # lower-left triangle
                pts = f"{x},{y} {x},{y + cell} {x + cell},{y + cell}"
            else:                  # upper-right triangle
                pts = f"{x},{y} {x + cell},{y} {x + cell},{y + cell}"
            out.append(f'<polygon points="{pts}" fill="{col}"/>')
    return "\n".join(out)


def text(x, y, s, size, weight="normal", fill=WHITE, opacity=1):
    return (f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" fill="{fill}" '
            f'fill-opacity="{opacity}">{s}</text>')


def banner(w, h, photo, cell, grid_cols, grid_rows, circle, title_y, title_size, info_y):
    cx, cy, r = circle
    img_w = 2 * r
    lines = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" font-family="{FONT}">',
             f'<rect width="{w}" height="{h}" fill="{MAGENTA}"/>',
             triangles(w - cell * grid_cols, 0, cell, grid_cols, grid_rows),
             f'<clipPath id="c"><circle cx="{cx}" cy="{cy}" r="{r}"/></clipPath>',
             f'<image href="{photo}" x="{cx - r}" y="{cy - r}" width="{img_w}" height="{img_w}" '
             f'preserveAspectRatio="xMidYMid slice" clip-path="url(#c)"/>']
    y = title_y
    for t in TITLE:
        lines.append(text(70, y, t, title_size, "bold")); y += round(title_size * 1.12)
    lines.append(text(70, y + round(title_size * 0.45), SPEAKER, round(title_size * 0.52), "500"))
    lines.append(text(70, y + round(title_size * 0.45) + round(title_size * 0.5), ROLE, round(title_size * 0.36), fill=WHITE, opacity=0.85))
    y = info_y
    s_big, s_small = round(title_size * 0.42), round(title_size * 0.36)
    lines.append(text(70, y, WHEN[0], s_big, "bold")); y += round(s_big * 1.35)
    lines.append(text(70, y, WHEN[1], s_big)); y += round(s_big * 2.0)
    lines.append(text(70, y, WHERE[0], s_small, "bold", opacity=0.95)); y += round(s_small * 1.4)
    lines.append(text(70, y, WHERE[1], s_small, opacity=0.95))
    lines.append("</svg>")
    return "\n".join(lines)


def chrome():
    for c in [os.environ.get("CHROME_PATH"), "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
              "/usr/bin/google-chrome", "/usr/bin/google-chrome-stable", "/usr/bin/chromium"]:
        if c and os.access(c, os.X_OK):
            return c
    sys.exit("make_banners: no Chrome found; set CHROME_PATH")


def render(svg_path, png_path, w, h):
    with tempfile.TemporaryDirectory() as d:
        subprocess.run([chrome(), "--headless=new", "--hide-scrollbars", f"--user-data-dir={d}",
                        f"--window-size={w},{h}", f"--screenshot={png_path}",
                        "file://" + os.path.abspath(svg_path)], check=True, capture_output=True, stdin=subprocess.DEVNULL)


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    photo = photo_data_uri(HEADSHOT)
    specs = {
        (1200, 675): dict(cell=90, grid_cols=4, grid_rows=2, circle=(985, 445), title_y=150, title_size=60, info_y=440),
        (1080, 1080): dict(cell=100, grid_cols=4, grid_rows=2, circle=(790, 820), title_y=330, title_size=72, info_y=640),
    }
    for (w, h), spec in specs.items():
        r = 195 if w == 1200 else 215
        spec["circle"] = (*spec["circle"], r)
        svg = banner(w, h, photo, **spec)
        name = f"banner-{w}x{h}"
        with open(name + ".svg", "w") as f:
            f.write(svg)
        render(name + ".svg", name + ".png", w, h)
        print("wrote", name + ".svg", name + ".png")


if __name__ == "__main__":
    main()
