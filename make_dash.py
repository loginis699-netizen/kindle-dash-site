#!/usr/bin/env python3
"""Generates a 600x800 8-bit grayscale PNG dashboard for a Kindle (KT2).

Usage:
  python3 make_dash.py out.png            # live weather from Open-Meteo (no API key)
  python3 make_dash.py out.png --demo     # sample data, no network
  add --no-clock for static hosting (no big clock, shows "updated" time)
Requires: Pillow.  Fonts: DejaVu Sans (change FONT_* paths if needed).
"""
import json
import sys
import urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo

from PIL import Image, ImageDraw, ImageFont

W, H = 600, 800
TZ = ZoneInfo("Europe/Vilnius")
LAT, LON = 54.6872, 25.2797  # Vilnius
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

WEEKDAYS = ["Pirmadienis", "Antradienis", "Trečiadienis", "Ketvirtadienis",
            "Penktadienis", "Šeštadienis", "Sekmadienis"]
WEEKDAYS_SHORT = ["Pr", "An", "Tr", "Kt", "Pn", "Št", "Sk"]
MONTHS = ["sausio", "vasario", "kovo", "balandžio", "gegužės", "birželio",
          "liepos", "rugpjūčio", "rugsėjo", "spalio", "lapkričio", "gruodžio"]


def wmo(code):
    """WMO weather code -> (Lithuanian text, icon kind)."""
    if code == 0:
        return "Giedra", "sun"
    if code in (1, 2):
        return "Mažai debesuota", "partly"
    if code == 3:
        return "Debesuota", "cloud"
    if code in (45, 48):
        return "Rūkas", "fog"
    if code in (51, 53, 55, 56, 57):
        return "Dulksna", "rain"
    if code in (61, 63, 65, 66, 67, 80, 81, 82):
        return "Lietus", "rain"
    if code in (71, 73, 75, 77, 85, 86):
        return "Sniegas", "snow"
    if code in (95, 96, 99):
        return "Perkūnija", "storm"
    return "—", "cloud"


def fetch_weather():
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={LAT}&longitude={LON}"
        "&current=temperature_2m,apparent_temperature,weather_code,wind_speed_10m"
        "&hourly=temperature_2m,precipitation_probability"
        "&daily=weather_code,temperature_2m_max,temperature_2m_min,sunrise,sunset"
        "&timezone=Europe%2FVilnius&forecast_days=4"
    )
    with urllib.request.urlopen(url, timeout=20) as r:
        return json.load(r)


def demo_weather():
    return {
        "current": {"temperature_2m": 2.4, "apparent_temperature": -0.8,
                    "weather_code": 3, "wind_speed_10m": 14.0},
        "hourly": demo_hourly(),
        "daily": {
            "time": ["2026-11-23", "2026-11-24", "2026-11-25", "2026-11-26"],
            "weather_code": [3, 61, 71, 0],
            "temperature_2m_max": [3.1, 4.0, 0.5, -1.2],
            "temperature_2m_min": [-0.5, 1.2, -2.0, -4.8],
            "sunrise": ["2026-11-23T07:46"] * 4,
            "sunset": ["2026-11-23T15:52"] * 4,
        },
    }


def demo_hourly():
    from datetime import timedelta
    t0 = datetime(2026, 11, 23, 0, 0)
    temps = [2.4, 2.0, 1.8, 1.5, 1.4, 1.6, 2.2, 3.0, 3.8, 4.1, 4.3, 4.0, 3.5, 3.0,
             2.6, 2.4, 2.2, 2.0, 1.9, 1.8, 1.7, 1.6, 1.5, 1.4]
    prob = [5, 5, 10, 10, 15, 20, 35, 55, 70, 60, 45, 30, 20, 15, 10, 5, 5, 5, 0, 0, 0, 0, 0, 0]
    times = [(t0 + timedelta(hours=i)).strftime("%Y-%m-%dT%H:00") for i in range(48)]
    return {"time": times, "temperature_2m": (temps * 2)[:48],
            "precipitation_probability": (prob * 2)[:48]}


def icon(d, kind, cx, cy, s):
    """Very simple monochrome weather icons, size ~ s."""
    k = 0
    if kind in ("sun", "partly"):
        r = s // 4
        ox, oy = (-s // 6, -s // 6) if kind == "partly" else (0, 0)
        d.ellipse([cx + ox - r, cy + oy - r, cx + ox + r, cy + oy + r], outline=k, width=4)
        if kind == "sun":
            import math
            for a in range(0, 360, 45):
                x1 = cx + (r + 6) * math.cos(math.radians(a))
                y1 = cy + (r + 6) * math.sin(math.radians(a))
                x2 = cx + (r + 16) * math.cos(math.radians(a))
                y2 = cy + (r + 16) * math.sin(math.radians(a))
                d.line([x1, y1, x2, y2], fill=k, width=3)
    if kind in ("cloud", "partly", "rain", "snow", "storm", "fog"):
        oy = s // 10 if kind != "partly" else s // 6
        ox = 0 if kind != "partly" else s // 8
        def shape(draw, grow, fill):
            g = grow
            draw.ellipse([cx - s // 3 + ox - g, cy - s // 12 + oy - g, cx - s // 12 + ox + g, cy + s // 5 + oy + g], fill=fill)
            draw.ellipse([cx - s // 5 + ox - g, cy - s // 4 + oy - g, cx + s // 8 + ox + g, cy + s // 8 + oy + g], fill=fill)
            draw.ellipse([cx - s // 24 + ox - g, cy - s // 5 + oy - g, cx + s // 3 + ox + g, cy + s // 6 + oy + g], fill=fill)
            draw.rounded_rectangle([cx - s // 4 + ox - g, cy - s // 20 + oy - g, cx + s // 4 + ox + g, cy + s // 5 + oy + g], radius=s // 10, fill=fill)
        shape(d, 3, k)      # black outline silhouette
        shape(d, -1, 255)   # white inside
    if kind in ("rain", "storm"):
        for dx in (-s // 6, 0, s // 6):
            d.line([cx + dx, cy + s // 3 + 6, cx + dx - 6, cy + s // 2 + 6], fill=k, width=3)
    if kind == "snow":
        for dx in (-s // 6, 0, s // 6):
            d.ellipse([cx + dx - 3, cy + s // 3 + 8, cx + dx + 3, cy + s // 3 + 14], fill=k)
    if kind == "fog":
        for i in range(3):
            d.line([cx - s // 3, cy + s // 3 + i * 8, cx + s // 3, cy + s // 3 + i * 8], fill=k, width=3)


def center(d, text, y, font, fill=0, x0=0, x1=W):
    w = d.textlength(text, font=font)
    d.text((x0 + (x1 - x0 - w) / 2, y), text, font=font, fill=fill)


def hourly_slice(data, now, n=12):
    h = data["hourly"]
    start = now.replace(minute=0, second=0, microsecond=0, tzinfo=None)
    times = [datetime.fromisoformat(t) for t in h["time"]]
    idx = next((i for i, t in enumerate(times) if t >= start), 0)
    out = []
    for i in range(idx, min(idx + n, len(times))):
        pp = h["precipitation_probability"][i]
        out.append((times[i], h["temperature_2m"][i], pp if pp is not None else 0))
    return out


def draw_hourly(d, f, rows, y0):
    """Temperature line + precipitation-probability bars for the next hours."""
    x_l, x_r = 55, W - 55
    n = len(rows)
    step = (x_r - x_l) / max(n - 1, 1)
    xs = [x_l + i * step for i in range(n)]
    temps = [r[1] for r in rows]
    tmin, tmax = min(temps), max(temps)
    span = max(tmax - tmin, 2.0)
    ty0, ty1 = y0 + 50, y0 + 98         # temperature band (top..bottom)
    ys = [ty1 - (t - tmin) / span * (ty1 - ty0) for t in temps]

    center(d, "Kitos valandos: linija \u2013 temperatūra, stulpeliai \u2013 lietaus tikimybė", y0, f(15))

    # precipitation bars (base line at y0+140)
    base, maxh = y0 + 140, 36
    bw = 22
    for x, (_, _, pp) in zip(xs, rows):
        h = int(pp / 100 * maxh)
        d.rectangle([x - bw // 2, base - maxh, x + bw // 2, base], outline=200)
        if h > 0:
            d.rectangle([x - bw // 2, base - h, x + bw // 2, base], fill=70)
    d.line([x_l - 14, base, x_r + 14, base], fill=0, width=2)

    # temperature line
    d.line(list(zip(xs, ys)), fill=0, width=3)
    for x, y in zip(xs, ys):
        d.ellipse([x - 4, y - 4, x + 4, y + 4], fill=0)
    for i, (x, y, t) in enumerate(zip(xs, ys, temps)):
        if i % 2 == 0:
            txt = f"{t:+.0f}\u00b0"
            w = d.textlength(txt, font=f(17, True))
            d.text((x - w / 2, y - 27), txt, font=f(17, True), fill=0)

    # hour labels + % under bars
    for i, (x, (t, _, pp)) in enumerate(zip(xs, rows)):
        lab = f"{t.hour:02d}"
        w = d.textlength(lab, font=f(16, True))
        d.text((x - w / 2, base + 4), lab, font=f(16, True), fill=0)
        if i % 2 == 0 and pp >= 10:
            pt = f"{pp}%"
            w = d.textlength(pt, font=f(13))
            d.text((x - w / 2, base + 22), pt, font=f(13), fill=0)


def render(data, now, clock=True):
    img = Image.new("L", (W, H), 255)
    d = ImageDraw.Draw(img)
    f = lambda sz, b=False: ImageFont.truetype(FONT_B if b else FONT, sz)

    # Header: date (no big clock when hosted statically)
    if clock:
        center(d, now.strftime("%H:%M"), 0, f(100, True))
        center(d, WEEKDAYS[now.weekday()], 112, f(30, True))
        center(d, f"{now.year} m. {MONTHS[now.month - 1]} {now.day} d.", 148, f(22))
    else:
        center(d, str(now.day), -6, f(110, True))
        center(d, WEEKDAYS[now.weekday()], 112, f(30, True))
        center(d, f"{now.year} m. {MONTHS[now.month - 1]}", 148, f(22))
        center(d, f"atnaujinta {now.strftime('%H:%M')}", 178, f(14))
    d.line([40, 202, W - 40, 202], fill=0, width=3)

    # Current weather
    cur = data["current"]
    text, kind = wmo(cur["weather_code"])
    icon(d, kind, 115, 275, 100)
    d.text((215, 215), f"{cur['temperature_2m']:+.0f}\u00b0", font=f(80, True), fill=0)
    d.text((217, 308), text, font=f(26), fill=0)
    d.text((217, 344), f"Jaučiasi kaip {cur['apparent_temperature']:+.0f}\u00b0  \u00b7  vėjas {cur['wind_speed_10m']:.0f} km/h",
           font=f(16), fill=0)
    d.line([40, 380, W - 40, 380], fill=0, width=3)

    # Hourly forecast
    draw_hourly(d, f, hourly_slice(data, now), 392)
    d.line([40, 590, W - 40, 590], fill=0, width=3)

    # 3-day forecast
    day = data["daily"]
    colw = (W - 80) // 3
    for i in range(1, 4):
        x0 = 40 + (i - 1) * colw
        x1 = x0 + colw
        dt = datetime.fromisoformat(day["time"][i])
        t, k = wmo(day["weather_code"][i])
        center(d, WEEKDAYS_SHORT[dt.weekday()] + f" {dt.day}", 598, f(22, True), x0=x0, x1=x1)
        icon(d, k, (x0 + x1) // 2, 650, 62)
        center(d, f"{day['temperature_2m_max'][i]:+.0f}\u00b0 / {day['temperature_2m_min'][i]:+.0f}\u00b0",
               690, f(20, True), x0=x0, x1=x1)
        center(d, t, 718, f(15), x0=x0, x1=x1)

    d.line([40, 745, W - 40, 745], fill=0, width=3)
    sr = day["sunrise"][0][11:16]
    ss = day["sunset"][0][11:16]
    center(d, f"Saulėtekis {sr}   \u00b7   Saulėlydis {ss}", 761, f(17))
    return img


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "dash.png"
    demo = "--demo" in sys.argv
    now = datetime.now(TZ)
    if demo:
        now = datetime(2026, 11, 23, 0, 10, tzinfo=TZ)
        data = demo_weather()
    else:
        data = fetch_weather()
    img = render(data, now, clock="--no-clock" not in sys.argv)
    img.save(out, "PNG", optimize=True)  # mode L, 8-bit gray, no alpha
    print(f"wrote {out} ({img.size[0]}x{img.size[1]}, {img.mode})")


if __name__ == "__main__":
    main()
