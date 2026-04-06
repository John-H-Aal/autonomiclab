"""Generate AutonomicLab icon and splash screen."""

import math
from PIL import Image, ImageDraw, ImageFont

RED        = (237, 28,  46)
WHITE      = (255, 255, 255)
DARK_BLUE  = (18,  30,  48)
TEAL       = (0,   210, 180)
LIGHT_BLUE = (160, 200, 220)


def heart_polygon(cx, cy, scale, steps=300):
    """Heart using parametric formula. scale ≈ pixels per unit."""
    pts = []
    for i in range(steps):
        t = 2 * math.pi * i / steps
        x =  16 * math.sin(t) ** 3
        y = -(13 * math.cos(t)
              - 5  * math.cos(2 * t)
              - 2  * math.cos(3 * t)
              -      math.cos(4 * t))
        pts.append((cx + x * scale, cy + y * scale))
    return pts


def draw_heart_outline(draw, cx, cy, scale, lw, color, bg=WHITE):
    """Draw a filled outline heart (outer RED fill, inner WHITE fill)."""
    delta = lw / 17
    outer = heart_polygon(cx, cy, scale + delta, steps=300)
    inner = heart_polygon(cx, cy, scale - delta, steps=300)
    draw.polygon(outer, fill=color)
    draw.polygon(inner, fill=bg)


def ecg_beat(px, py, t0, t1):
    """One realistic ECG beat from fraction t0 to t1."""
    def t(f): return t0 + f * (t1 - t0)
    return [
        (px(t(0.00)), py( 0.00)),   # isoelectric
        (px(t(0.10)), py( 0.00)),
        (px(t(0.13)), py( 0.12)),   # P wave up
        (px(t(0.17)), py( 0.15)),   # P wave peak
        (px(t(0.21)), py( 0.12)),
        (px(t(0.25)), py( 0.00)),   # P wave end
        (px(t(0.30)), py( 0.00)),   # PR segment
        (px(t(0.35)), py(-0.08)),   # Q dip
        (px(t(0.39)), py(-0.12)),
        (px(t(0.41)), py(-0.06)),
        (px(t(0.43)), py(-1.00)),   # R peak ← sharp
        (px(t(0.45)), py(-0.06)),
        (px(t(0.47)), py( 0.28)),   # S wave
        (px(t(0.50)), py( 0.10)),
        (px(t(0.53)), py( 0.00)),   # ST segment
        (px(t(0.58)), py( 0.00)),
        (px(t(0.62)), py(-0.05)),   # T wave start
        (px(t(0.67)), py(-0.28)),   # T wave peak
        (px(t(0.72)), py(-0.22)),
        (px(t(0.77)), py(-0.05)),
        (px(t(0.80)), py( 0.00)),   # T wave end
        (px(t(0.85)), py( 0.00)),   # TP segment
        (px(t(1.00)), py( 0.00)),
    ]


def draw_ecg(draw, x0, x1, mid_y, h, lw, color):
    """Two realistic ECG beats across the full width."""
    def px(f): return x0 + f * (x1 - x0)
    def py(f): return mid_y + f * h

    pts = (
        ecg_beat(px, py, 0.00, 0.48) +
        ecg_beat(px, py, 0.48, 0.96) +
        [(px(0.96), py(0.00)), (px(1.00), py(0.00))]
    )
    draw.line(pts, fill=color, width=lw, joint="curve")


# ── icon ──────────────────────────────────────────────────────────────────────

def draw_icon(size: int) -> Image.Image:
    s   = size
    lw  = max(2, round(s / 26))       # consistent line width

    img  = Image.new("RGBA", (s, s), WHITE + (255,))
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, s, s], fill=WHITE)

    # Monitor square: top-left, ~73% of image
    sq0  = round(s * 0.07)
    sq1  = round(s * 0.76)
    rad  = round(s * 0.07)
    draw.rounded_rectangle([sq0, sq0, sq1, sq1],
                            radius=rad, fill=WHITE, outline=RED, width=lw)

    # ECG inside the square
    pad  = round(s * 0.12)
    ecg_x0  = sq0 + pad
    ecg_x1  = sq1 - pad // 2
    ecg_mid = round((sq0 + sq1) / 2) - round(s * 0.03)
    ecg_h   = round((sq1 - sq0) * 0.36)
    draw_ecg(draw, ecg_x0, ecg_x1, ecg_mid, ecg_h, lw, RED)

    # Heart: bottom-right, overlapping square corner
    hcx    = round(s * 0.720)
    hcy    = round(s * 0.740)
    hscale = s * 0.014

    draw_heart_outline(draw, hcx, hcy, hscale, lw, RED, WHITE)

    return img


def make_icon():
    # Draw at high resolution, let PIL resize to all needed sizes
    base = draw_icon(256).convert("RGBA")
    base.save(
        "assets/autonomiclab.ico",
        format="ICO",
        sizes=[(16,16), (32,32), (48,48), (64,64), (128,128), (256,256)],
    )
    base.save("autonomiclab_icon_preview.png")
    print("icon  → assets/autonomiclab.ico")


# ── splash ────────────────────────────────────────────────────────────────────

def make_splash():
    W, H = 500, 280
    img  = Image.new("RGBA", (W, H), (0, 0, 0, 0))   # transparent
    draw = ImageDraw.Draw(img)

    draw.rounded_rectangle([2, 2, W-3, H-3], radius=18,
                            fill=DARK_BLUE + (255,), outline=TEAL, width=3)

    mid = H // 2 + 55
    draw_ecg(draw, 20, W-20, mid, h=65, lw=3, color=TEAL)

    try:
        font_title = ImageFont.truetype(
            "/usr/share/fonts/liberation/LiberationSans-Bold.ttf", 44)
        font_sub   = ImageFont.truetype(
            "/usr/share/fonts/liberation/LiberationSans-Regular.ttf", 18)
    except Exception:
        font_title = ImageFont.load_default()
        font_sub   = font_title

    for text, font, color, y in [
        ("AutonomicLab",           font_title, WHITE,      22),
        ("GAT Protocol Analysis",  font_sub,   LIGHT_BLUE, 78),
        ("Loading...",             font_sub,   LIGHT_BLUE, H - 38),
    ]:
        tw = draw.textlength(text, font=font)
        draw.text(((W - tw) / 2, y), text, font=font, fill=color)

    img.save("assets/autonomiclab_splash.png")
    print("splash → assets/autonomiclab_splash.png")


if __name__ == "__main__":
    make_icon()
    make_splash()
