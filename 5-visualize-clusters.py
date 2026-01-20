#!/usr/bin/env python3

import argparse
import base64
import csv
import http.server
import io
import os
import webbrowser
from PIL import Image

try:
    import cairosvg
except ImportError:
    cairosvg = None

DATA_DIR = "./data"
MANIFEST_FILE = os.path.join(DATA_DIR, "staged-logos.csv")
THUMB_SIZE = (64, 64)


def load_image_as_base64(file_path: str) -> str | None:
    if not os.path.exists(file_path):
        return None
    try:
        if file_path.lower().endswith(".svg"):
            if cairosvg is None:
                return None
            png_data = cairosvg.svg2png(
                url=file_path, output_width=128, output_height=128
            )
            if png_data is None:
                return None
            img = Image.open(io.BytesIO(png_data)).convert("RGBA")
        else:
            img = Image.open(file_path).convert("RGBA")

        background = Image.new("RGBA", img.size, (255, 255, 255, 255))
        background.paste(img, mask=img.split()[3])
        img = background.convert("RGB")
        img.thumbnail(THUMB_SIZE, Image.Resampling.LANCZOS)

        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        return base64.b64encode(buffer.getvalue()).decode("utf-8")
    except Exception:
        return None


def parse_cluster_report(path: str) -> tuple[list[list[str]], list[str]]:
    clusters: list[list[str]] = []
    singletons: list[str] = []
    current_cluster: list[str] = []
    in_singletons = False

    with open(path) as f:
        for line in f:
            line = line.strip()
            if line.startswith("=== Cluster"):
                if current_cluster:
                    clusters.append(current_cluster)
                current_cluster = []
            elif line == "=== Singletons ===":
                if current_cluster:
                    clusters.append(current_cluster)
                current_cluster = []
                in_singletons = True
            elif line and not line.startswith("#"):
                if in_singletons:
                    singletons.append(line)
                else:
                    current_cluster.append(line)

    return clusters, singletons


def generate_html() -> str:
    print(f"Reading manifest: {MANIFEST_FILE}")
    domain_to_path: dict[str, str] = {}
    with open(MANIFEST_FILE) as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["local_path"] and row["domain"]:
                domain_to_path[row["domain"]] = row["local_path"]

    print("Parsing cluster report...")
    clusters, singletons = parse_cluster_report("cluster_report.txt")

    print("Loading images...")
    images: dict[str, str] = {}
    all_domains = [d for c in clusters for d in c] + singletons
    for domain in all_domains:
        path = domain_to_path.get(domain)
        if path:
            b64 = load_image_as_base64(path)
            if b64:
                images[domain] = b64

    print(
        f"Generating HTML ({len(clusters)} clusters, {len(singletons)} singletons)..."
    )

    html = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Logo Clusters</title>
<style>
body { font-family: system-ui, sans-serif; margin: 20px; background: #f5f5f5; }
h1 { color: #333; }
.cluster { background: white; padding: 15px; margin: 10px 0; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
.cluster h2 { margin: 0 0 10px 0; font-size: 14px; color: #666; }
.logos { display: flex; flex-wrap: wrap; gap: 10px; }
.logo { text-align: center; width: 80px; }
.logo img { width: 64px; height: 64px; object-fit: contain; border: 1px solid #eee; background: white; }
.logo span { display: block; font-size: 9px; color: #888; word-break: break-all; margin-top: 4px; }
.singletons { opacity: 0.6; }
.stats { background: #333; color: white; padding: 10px 15px; border-radius: 8px; margin-bottom: 20px; }
</style>
</head>
<body>
<h1>Logo Clusters</h1>
<div class="stats">
"""
    html += f"<strong>{len(clusters)}</strong> clusters with multiple logos, "
    html += f"<strong>{len(singletons)}</strong> singletons"
    html += "</div>\n"

    for i, cluster in enumerate(clusters, 1):
        html += f'<div class="cluster"><h2>Cluster {i} ({len(cluster)} logos)</h2><div class="logos">\n'
        for domain in cluster:
            if domain in images:
                html += f'<div class="logo"><img src="data:image/png;base64,{images[domain]}"><span>{domain}</span></div>\n'
            else:
                html += f'<div class="logo"><div style="width:64px;height:64px;background:#eee"></div><span>{domain}</span></div>\n'
        html += "</div></div>\n"

    html += '<div class="cluster singletons"><h2>Singletons</h2><div class="logos">\n'
    for domain in singletons:
        if domain in images:
            html += f'<div class="logo"><img src="data:image/png;base64,{images[domain]}"><span>{domain}</span></div>\n'
    html += "</div></div>\n"

    html += "</body></html>"
    return html


def make_handler(html_content: str):
    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(html_content.encode())

        def log_message(self, format, *args):
            pass

    return Handler


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", "-p", type=int, default=8000)
    args = parser.parse_args()

    html = generate_html()
    url = f"http://localhost:{args.port}"
    print(f"Serving at {url}")
    webbrowser.open(url)

    handler = make_handler(html)
    with http.server.HTTPServer(("", args.port), handler) as httpd:
        httpd.serve_forever()


if __name__ == "__main__":
    main()
