#!/usr/bin/env python3

import csv
import io
import os
from collections import defaultdict
from PIL import Image

try:
    import imagehash
except ImportError:
    print("Error: imagehash is not installed. Please run: pip install imagehash")
    exit(1)

try:
    import cairosvg
except ImportError:
    cairosvg = None

DATA_DIR = "./data"
MANIFEST_FILE = os.path.join(DATA_DIR, "staged-logos.csv")
OUTPUT_FILE = "cluster_report.txt"
HASH_THRESHOLD = 8


def main():
    if not os.path.exists(MANIFEST_FILE):
        print(f"Error: Manifest file '{MANIFEST_FILE}' not found.")
        print("Did you run '3-download-logos.sh'?")
        return

    print(f"Reading manifest: {MANIFEST_FILE}")
    entries = []
    with open(MANIFEST_FILE, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["local_path"] and row["domain"]:
                entries.append((row["domain"], row["local_path"]))

    print(f"Found {len(entries)} entries in manifest.")

    print("Computing perceptual hashes...")
    hashes: dict[str, imagehash.ImageHash] = {}
    for domain, file_path in entries:
        img = load_image(file_path)
        if img:
            hashes[domain] = compute_hash(img)

    print(f"Successfully hashed {len(hashes)} logos.")

    print(f"Clustering with Hamming distance threshold = {HASH_THRESHOLD}...")
    domains = list(hashes.keys())
    parent = {d: d for d in domains}
    rank = {d: 0 for d in domains}

    for i, d1 in enumerate(domains):
        for d2 in domains[i + 1 :]:
            distance = hashes[d1] - hashes[d2]
            if distance <= HASH_THRESHOLD:
                union_clusters(parent, rank, d1, d2)

    clusters: dict[str, list[str]] = defaultdict(list)
    for domain in domains:
        root = find_cluster(parent, domain)
        clusters[root].append(domain)

    multi_clusters = {k: v for k, v in clusters.items() if len(v) > 1}
    singletons = [k for k, v in clusters.items() if len(v) == 1]

    print(f"Found {len(multi_clusters)} clusters with multiple logos.")
    print(f"Found {len(singletons)} singleton logos (no matches).")

    with open(OUTPUT_FILE, "w") as f:
        f.write("# Logo Clustering Report (Perceptual Hash)\n")
        f.write(f"# Threshold: Hamming distance <= {HASH_THRESHOLD}\n")
        f.write(f"# Total logos: {len(hashes)}\n")
        f.write(f"# Clusters (2+ logos): {len(multi_clusters)}\n")
        f.write(f"# Singletons: {len(singletons)}\n\n")

        sorted_clusters = sorted(multi_clusters.items(), key=lambda x: -len(x[1]))

        for i, (root, members) in enumerate(sorted_clusters, 1):
            f.write(f"=== Cluster {i} ({len(members)} logos) ===\n")
            for domain in sorted(members):
                f.write(f"  {domain}\n")
            f.write("\n")

        f.write("=== Singletons ===\n")
        for domain in sorted(singletons):
            f.write(f"  {domain}\n")

    print(f"Report saved to '{OUTPUT_FILE}'.")


def load_image(file_path: str) -> Image.Image | None:
    if not os.path.exists(file_path):
        return None
    try:
        if file_path.lower().endswith(".svg"):
            if cairosvg is None:
                print(f"  Warning: cairosvg not installed, skipping {file_path}")
                return None
            png_data = cairosvg.svg2png(
                url=file_path, output_width=256, output_height=256
            )
            if png_data is None:
                return None
            img = Image.open(io.BytesIO(png_data)).convert("RGBA")
        else:
            img = Image.open(file_path).convert("RGBA")
        background = Image.new("RGBA", img.size, (255, 255, 255, 255))
        background.paste(img, mask=img.split()[3])
        return background.convert("RGB")
    except Exception as e:
        print(f"  Warning: Failed to load {file_path}: {e}")
        return None


def compute_hash(img: Image.Image) -> imagehash.ImageHash:
    return imagehash.phash(img)


def find_cluster(parent: dict, x: str) -> str:
    if parent[x] != x:
        parent[x] = find_cluster(parent, parent[x])
    return parent[x]


def union_clusters(parent: dict, rank: dict, x: str, y: str) -> None:
    root_x = find_cluster(parent, x)
    root_y = find_cluster(parent, y)
    if root_x != root_y:
        if rank[root_x] < rank[root_y]:
            parent[root_x] = root_y
        elif rank[root_x] > rank[root_y]:
            parent[root_y] = root_x
        else:
            parent[root_y] = root_x
            rank[root_x] += 1


if __name__ == "__main__":
    main()
