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
        "&daily=weather_code,temperature_2m_max,temperature_2m_min,sunrise,sunset"
        "&timezone=Europe%2FVilnius&forecast_days=4"
    )
    with urllib.request.urlopen(url, timeout=20) as r:
        return json.load(r)


def demo_weather():
    return {
        "current": {"temperature_2m": 2.4, "apparent_temperature": -0.8,
                    "weather_code": 3, "wind_speed_10m": 14.0},
        "daily": {
            "time": ["2026-11-23", "2026-11-24", "2026-11-25", "2026-11-26"],
            "weather_code": [3, 61, 71, 0],
            "temperature_2m_max": [3.1, 4.0, 0.5, -1.2],
            "temperature_2m_min": [-0.5, 1.2, -2.0, -4.8],
            "sunrise": ["2026-11-23T07:46"] * 4,
            "sunset": ["2026-11-23T15:52"] * 4,
        },
    }


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


def render(data, now, clock=True):
    img = Image.new("L", (W, H), 255)
    d = ImageDraw.Draw(img)
    f = lambda sz, b=False: ImageFont.truetype(FONT_B if b else FONT, sz)

    # Header: time and date
    if clock:
        center(d, now.strftime("%H:%M"), 14, f(130, True))
        center(d, WEEKDAYS[now.weekday()], 160, f(36, True))
        center(d, f"{now.year} m. {MONTHS[now.month - 1]} {now.day} d.", 205, f(28))
    else:
        # Static hosting: image is re-rendered only every ~15 min, so no big clock.
        center(d, str(now.day), 0, f(150, True))
        center(d, WEEKDAYS[now.weekday()], 160, f(36, True))
        center(d, f"{now.year} m. {MONTHS[now.month - 1]}", 205, f(28))
        center(d, f"atnaujinta {now.strftime('%H:%M')}", 236, f(16))
    d.line([40, 255, W - 40, 255], fill=0, width=3)

    # Current weather
    cur = data["current"]
    text, kind = wmo(cur["weather_code"])
    icon(d, kind, 130, 345, 120)
    d.text((230, 285), f"{cur['temperature_2m']:+.0f}°", font=f(96, True), fill=0)
    d.text((232, 395), text, font=f(30), fill=0)
    d.text((232, 435), f"Jaučiasi kaip {cur['apparent_temperature']:+.0f}°  ·  vėjas {cur['wind_speed_10m']:.0f} km/h", font=f(18), fill=0)
    d.line([40, 485, W - 40, 485], fill=0, width=3)

    # 3-day forecast
    day = data["daily"]
    colw = (W - 80) // 3
    for i in range(1, 4):
        x0 = 40 + (i - 1) * colw
        x1 = x0 + colw
        dt = datetime.fromisoformat(day["time"][i])
        t, k = wmo(day["weather_code"][i])
        center(d, WEEKDAYS_SHORT[dt.weekday()] + f" {dt.day}", 505, f(26, True), x0=x0, x1=x1)
        icon(d, k, (x0 + x1) // 2, 600, 80)
        center(d, f"{day['temperature_2m_max'][i]:+.0f}° / {day['temperature_2m_min'][i]:+.0f}°", 665, f(24, True), x0=x0, x1=x1)
        center(d, t, 700, f(18), x0=x0, x1=x1)

    d.line([40, 740, W - 40, 740], fill=0, width=3)
    sr = day["sunrise"][0][11:16]
    ss = day["sunset"][0][11:16]
    center(d, f"Saulėtekis {sr}   ·   Saulėlydis {ss}", 755, f(20))
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
