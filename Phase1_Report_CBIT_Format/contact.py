import sys, pymupdf
from PIL import Image
pdf, first, last, out = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
d = pymupdf.open(pdf); ims = []
for i in range(first - 1, min(last, len(d))):
    pix = d[i].get_pixmap(dpi=55); ims.append(Image.frombytes("RGB", (pix.width, pix.height), pix.samples))
cols = 4; w = max(i.width for i in ims); h = max(i.height for i in ims)
rows = (len(ims) + cols - 1) // cols
sheet = Image.new("RGB", (cols * w, rows * h), "white")
for k, im in enumerate(ims): sheet.paste(im, ((k % cols) * w, (k // cols) * h))
sheet.save(out)
