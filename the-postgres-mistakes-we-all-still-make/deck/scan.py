"""Clipping scan for the built slide images: bottom band, right edge, and the footer region."""
import glob, sys, matplotlib.image as mpimg
res = []
for f in sorted(glob.glob("img/slide.*.png")):
    im = mpimg.imread(f)[:, :, :3]; h, w = im.shape[:2]; bg = im[2, 2]
    nz = lambda a: int((abs(a - bg).sum(axis=2) > 0.15).sum())
    res.append((f.split('.')[-2], nz(im[h-62:h-22, 120:w-110]), nz(im[60:h-70, w-6:w]), nz(im[650:672, 64:400])))
med = lambda i: sorted(r[i] for r in res)[len(res)//2]
b, fo = med(1), med(3)
print("slides:", len(res))
print("bottom band above baseline:", [(n, v) for n, v, _, _ in res if v > b + 300])
print("right edge content:", [n for n, _, v, _ in res if v > 30])
print("footer region above baseline (overlap):", [(n, v) for n, _, _, v in res if v > fo + 150])

flags = [r for r in res if r[1] > b + 300 or r[2] > 30 or r[3] > fo + 150]
sys.exit(1 if flags else 0)
