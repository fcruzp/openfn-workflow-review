"""Draw the same laid-out diagram as a PNG preview (all colors, legend and big title)."""
import math, os
from PIL import Image, ImageDraw, ImageFont
from .diagram_layout import waypoints, wrap

FONT_DIR = os.path.join(os.path.dirname(__file__), "style", "fonts")
SCALE = 1.4


def font(size):
    try:
        return ImageFont.truetype(os.path.join(FONT_DIR, "LiberationSans-Regular.ttf"), int(size * SCALE))
    except OSError:
        return ImageFont.load_default()


def render(lay, path):
    x0, y0, x1, y1 = lay["bounds"]
    W, H = int((x1 - x0) * SCALE), int((y1 - y0) * SCALE)
    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)
    P = lambda x, y: ((x - x0) * SCALE, (y - y0) * SCALE)
    R = lambda s: [*P(s["x"], s["y"]), *P(s["x"] + s["w"], s["y"] + s["h"])]
    f11, f12, f13 = font(11), font(12), font(13)

    def text_center(lines, cx, cy, f, lh=15):
        top = cy - lh * len(lines) / 2
        for i, l in enumerate(lines):
            d.text(P(cx, top + i * lh + lh / 2), l, fill="black", font=f, anchor="mm")

    def vertical_text(t, x, y, h, f):
        tw = int(d.textlength(t, font=f)) + 10
        tmp = Image.new("RGBA", (tw, int(20 * SCALE)), (255, 255, 255, 0))
        ImageDraw.Draw(tmp).text((5, 2), t, fill="black", font=f)
        tmp = tmp.rotate(90, expand=True)
        px, py = P(x, y + h / 2)
        img.paste(tmp, (int(px - tmp.width / 2), int(py - tmp.height / 2)), tmp)

    # legend and title
    for l in lay["legend"]:
        d.rounded_rectangle(R(l), radius=4 * SCALE, fill=l["fill"], outline="black", width=2)
        d.text(P(l["x"] + 8, l["y"] + l["h"] / 2), l["label"], fill="black", font=f12, anchor="lm")
    t = lay["title"]
    size = 72
    while size > 20 and d.textlength(t["label"], font=font(size)) > (t["w"] - 20) * SCALE:
        size -= 4
    d.text(P(t["x"], t["y"] + t["h"] / 2), t["label"], fill="black", font=font(size), anchor="lm")
    # pool and lanes
    p = lay["pool"]
    d.rectangle(R(p), outline="black", width=2)
    d.line([P(p["x"] + 30, p["y"]), P(p["x"] + 30, p["y"] + p["h"])], fill="black", width=2)
    vertical_text(p["name"], p["x"] + 15, p["y"], p["h"], f13)
    for ln in lay["lanes"]:
        d.rectangle(R(ln), outline="black", width=2)
        vertical_text(ln["name"], ln["x"] + 18, ln["y"], ln["h"], f13)

    def arrow(pts, dotted=False, open_head=False):
        pts = [P(*q) for q in pts]
        for a, b in zip(pts, pts[1:]):
            if dotted:
                L = math.dist(a, b)
                n = max(1, int(L / (5 * SCALE)))
                for i in range(0, n, 2):
                    t0, t1 = i / n, min(1, (i + 1) / n)
                    d.line([(a[0] + (b[0] - a[0]) * t0, a[1] + (b[1] - a[1]) * t0),
                            (a[0] + (b[0] - a[0]) * t1, a[1] + (b[1] - a[1]) * t1)], fill="black", width=2)
            else:
                d.line([a, b], fill="black", width=2)
        (ax, ay), (bx, by) = pts[-2], pts[-1]
        ang = math.atan2(by - ay, bx - ax)
        s = 9 * SCALE
        p1 = (bx - s * math.cos(ang - 0.4), by - s * math.sin(ang - 0.4))
        p2 = (bx - s * math.cos(ang + 0.4), by - s * math.sin(ang + 0.4))
        if open_head:
            d.line([p1, (bx, by), p2], fill="black", width=2)
        else:
            d.polygon([p1, (bx, by), p2], fill="black")

    for f in lay["flows"]:
        pts = waypoints(lay, f)
        arrow(pts)
        if f["label"]:
            (ax, ay), (bx, by) = pts[-2], pts[-1]
            d.text(P((ax + bx) / 2, min(ay, by) - 10), f["label"], fill="black", font=f11, anchor="mm")
    for a in lay["assocs"]:
        arrow(waypoints(lay, a, "assoc"), dotted=True, open_head=True)

    for s in lay["shapes"]:
        if s["type"] == "task":
            d.rounded_rectangle(R(s), radius=10 * SCALE, fill=s["fill"] or "white", outline="black", width=3)
            text_center(wrap(s["label"], s["w"] - 16), s.cx, s.cy, f13)
        elif s["type"] in ("startEvent", "endEvent"):
            d.ellipse(R(s), fill=s["fill"] or "white", outline="black", width=5 if s["type"] == "endEvent" else 2)
            if s["type"] == "startEvent":
                cx, cy = P(s.cx, s.cy)
                r = 10 * SCALE
                if s.get("trigger") == "cron":
                    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline="black", width=2)
                    d.line([(cx, cy), (cx, cy - r * 0.7)], fill="black", width=2)
                    d.line([(cx, cy), (cx + r * 0.5, cy)], fill="black", width=2)
                else:
                    d.rectangle([cx - r, cy - r * 0.65, cx + r, cy + r * 0.65], outline="black", width=2)
                    d.line([(cx - r, cy - r * 0.65), (cx, cy + r * 0.1), (cx + r, cy - r * 0.65)], fill="black", width=2)
            if s.get("label"):
                text_center(wrap(s["label"], 110), s.cx, s.bottom + 22, f11, 14)
        elif s["type"] == "parallelGateway":
            cx, cy = P(s.cx, s.cy)
            r = s["w"] / 2 * SCALE
            d.polygon([(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)], fill="white", outline="black", width=3)
            d.line([(cx - r * 0.45, cy), (cx + r * 0.45, cy)], fill="black", width=int(5 * SCALE))
            d.line([(cx, cy - r * 0.45), (cx, cy + r * 0.45)], fill="black", width=int(5 * SCALE))
        elif s["type"] == "dataObjectReference":
            x, y = s["x"], s["y"]
            fold = 9
            d.polygon([P(x, y), P(x + s["w"] - fold, y), P(x + s["w"], y + fold), P(x + s["w"], y + s["h"]),
                       P(x, y + s["h"])], fill="white", outline="black", width=2)
            d.line([P(x + s["w"] - fold, y), P(x + s["w"] - fold, y + fold), P(x + s["w"], y + fold)], fill="black", width=2)
            text_center(wrap(s["label"], 110), s.cx, s.bottom + 22, f11, 14)
        elif s["type"] == "dataStoreReference":
            x, y, w, h = s["x"], s["y"], s["w"], s["h"]
            e = 8
            d.rectangle([*P(x, y + e / 2), *P(x + w, y + h - e / 2)], fill=s["fill"], outline=None)
            d.line([P(x, y + e / 2), P(x, y + h - e / 2)], fill="black", width=2)
            d.line([P(x + w, y + e / 2), P(x + w, y + h - e / 2)], fill="black", width=2)
            d.ellipse([*P(x, y + h - e), *P(x + w, y + h)], fill=s["fill"], outline="black", width=2)
            d.ellipse([*P(x, y), *P(x + w, y + e)], fill=s["fill"], outline="black", width=2)
            d.arc([*P(x, y + 6), *P(x + w, y + 6 + e)], 0, 180, fill="black", width=2)
            text_center(wrap(s["label"], 110), s.cx, s.bottom + 22, f11, 14)
        elif s["type"] == "endpoint":
            bx, by = P(s["x"], s["y"])
            d.line([(bx + 8, by), (bx, by), (bx, by + s["h"] * SCALE), (bx + 8, by + s["h"] * SCALE)], fill="black", width=2)
            tx, ty = P(s["x"] + 8, s["y"] + s["h"] / 2)
            l, t, r, b = d.textbbox((tx, ty), s["label"], font=f12, anchor="lm")
            d.rectangle([l - 2, t - 2, r + 2, b + 2], fill="white")
            d.text((tx, ty), s["label"], fill="black", font=f12, anchor="lm")
    for n in lay["notes"]:
        d.rectangle(R(n), fill=n["fill"])
        bx, by = P(n["x"], n["y"])
        d.line([(bx + 10, by), (bx, by), (bx, by + n["h"] * SCALE), (bx + 10, by + n["h"] * SCALE)], fill="black", width=3)
        for i, l in enumerate(n["lines"]):
            d.text(P(n["x"] + 10, n["y"] + 8 + i * 20), l, fill="black", font=f13)
    img.save(path, optimize=True)
