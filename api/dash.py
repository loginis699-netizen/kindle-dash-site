"""Vercel serverless function: renders the Kindle dashboard on every request."""
import io
import os
import sys
from datetime import datetime
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import make_dash  # noqa: E402


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            q = parse_qs(urlparse(self.path).query)
            if "demo" in q:
                now = datetime(2026, 11, 23, 0, 10, tzinfo=make_dash.TZ)
                data = make_dash.demo_weather()
            else:
                now = datetime.now(make_dash.TZ)
                data = make_dash.fetch_weather()
            img = make_dash.render(data, now, clock=False)
            buf = io.BytesIO()
            img.save(buf, "PNG", optimize=True)
            body = buf.getvalue()
            self.send_response(200)
            self.send_header("Content-Type", "image/png")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "public, s-maxage=120, max-age=0")
            self.end_headers()
            self.wfile.write(body)
        except Exception as e:  # report as 502 so the Kindle keeps its old image
            msg = f"error: {e}".encode()
            self.send_response(502)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(msg)))
            self.end_headers()
            self.wfile.write(msg)
