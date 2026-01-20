#!/usr/bin/env python3

import sys
import json
import re
import argparse
from typing import Dict, List, Optional, Any, Union
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup, Tag


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Rank logo candidates from HTML stdin."
    )
    parser.add_argument(
        "url", help="The source URL of the page (for resolving relative links)"
    )
    args = parser.parse_args()

    base_url = args.url.strip()
    if not urlparse(base_url).scheme:
        base_url = f"https://{base_url}"

    html_input: str = sys.stdin.read()

    candidates = analyze_html(html_input, base_url)

    ranked = sorted(candidates.items(), key=lambda x: x[1]["score"], reverse=True)

    results = []
    for i, (url, data) in enumerate(ranked):
        results.append(
            {
                "rank": i + 1,
                "score": data["score"],
                "url": url,
                "signals": list(data["reasons"]),
            }
        )

    print(json.dumps(results, indent=4))


def normalize_url(base: str, url: Optional[str]) -> Optional[str]:
    if not url:
        return None

    url = url.strip()

    try:
        full_url = urljoin(base, url)

        if not full_url.lower().startswith(("http://", "https://")):
            return None

        return full_url
    except Exception:
        return None


def extract_domain_stem(url: str) -> str:
    try:
        netloc = urlparse(url).netloc
        if netloc.startswith("www."):
            netloc = netloc[4:]
        return netloc.split(".")[0].lower()
    except Exception:
        return ""


def is_home_link(base_url: str, href: Optional[str]) -> bool:
    if not href:
        return False

    abs_href = normalize_url(base_url, href)
    if not abs_href:
        return False

    base_parsed = urlparse(base_url)
    href_parsed = urlparse(abs_href)

    if base_parsed.netloc == href_parsed.netloc:
        if href_parsed.path in ["", "/", "/index.html", "/index.php"]:
            return True

    return False


def get_str_attr(tag: Tag, attr: str) -> Optional[str]:
    """Helper to safely get a string attribute from a BS4 tag."""
    val = tag.get(attr)
    if isinstance(val, str):
        return val
    if isinstance(val, list) and val:
        return str(val[0])
    return None


def analyze_html(html_content: str, base_url: str) -> Dict[str, Dict[str, Any]]:
    soup = BeautifulSoup(html_content, "html.parser")
    domain_stem = extract_domain_stem(base_url)

    candidates: Dict[str, Dict[str, Any]] = {}

    def update_candidate(url: Optional[str], score: int, reason: str) -> None:
        norm_url = normalize_url(base_url, url)
        if not norm_url:
            return

        if norm_url not in candidates:
            candidates[norm_url] = {"score": 0, "reasons": set()}

        candidates[norm_url]["reasons"].add(reason)
        if score > candidates[norm_url]["score"]:
            candidates[norm_url]["score"] = score

    scripts = soup.find_all("script", type="application/ld+json")
    for script in scripts:
        try:
            if not script.string:
                continue
            data = json.loads(script.string)

            def find_logo(obj: Union[Dict, List, str, Any]) -> List[str]:
                found: List[str] = []
                if isinstance(obj, dict):
                    if "@type" in obj and obj["@type"] in [
                        "Organization",
                        "Brand",
                        "Corporation",
                    ]:
                        if "logo" in obj:
                            logo_val = obj["logo"]
                            if isinstance(logo_val, str):
                                found.append(logo_val)
                            elif isinstance(logo_val, dict) and "url" in logo_val:
                                found.append(logo_val["url"])
                    for v in obj.values():
                        found.extend(find_logo(v))
                elif isinstance(obj, list):
                    for item in obj:
                        found.extend(find_logo(item))
                return found

            logos = find_logo(data)
            for logo_url in logos:
                update_candidate(logo_url, 60, "Schema.org Organization")
        except Exception:
            continue

    for link in soup.find_all(
        "link",
        rel=lambda x: x is not None
        and ("icon" in x.lower() or "apple-touch-icon" in x.lower()),
    ):
        href = get_str_attr(link, "href")
        if href:
            update_candidate(href, 10, "Favicon/Touch Icon")

    og_image = soup.find("meta", property="og:image")
    if og_image and isinstance(og_image, Tag):
        content = get_str_attr(og_image, "content")
        if content:
            update_candidate(content, 5, "OpenGraph Image")

    images = soup.find_all("img")

    positive_keywords = re.compile(r"logo|brand|identity", re.I)
    negative_keywords = re.compile(r"partner|client|sponsor|payment|manufacturer", re.I)

    for img in images:
        src_val = img.get("src")
        if not src_val or not isinstance(src_val, str):
            continue

        src: str = src_val

        score = 0
        reasons: List[str] = []

        parents = list(img.parents)
        parent_names = [p.name for p in parents]
        parent_classes: List[str] = []
        for p in parents:
            cls = p.get("class")
            if isinstance(cls, list):
                parent_classes.extend(cls)
            elif isinstance(cls, str):
                parent_classes.append(cls)

            pid = p.get("id")
            if isinstance(pid, str):
                parent_classes.append(pid)
            elif isinstance(pid, list):
                parent_classes.extend(pid)

        parent_class_str = " ".join([str(c) for c in parent_classes])

        anchors = [p for p in parents if p.name == "a"]
        if anchors:
            href_val = anchors[0].get("href")
            if isinstance(href_val, str):
                if is_home_link(base_url, href_val):
                    score += 50
                    reasons.append("Linked to Home")
                elif (
                    normalize_url(base_url, href_val)
                    and extract_domain_stem(normalize_url(base_url, href_val) or "")
                    != domain_stem
                ):
                    pass

        if "header" in parent_names or "header" in parent_class_str.lower():
            score += 10
            reasons.append("In Header")
        elif "footer" in parent_names or "footer" in parent_class_str.lower():
            score -= 30
            reasons.append("In Footer")

        alt_val = img.get("alt", "")
        if isinstance(alt_val, list):
            alt_val = " ".join(alt_val)
        if not isinstance(alt_val, str):
            alt_val = ""

        img_class_val = img.get("class", "")
        if isinstance(img_class_val, list):
            img_class_val = " ".join(img_class_val)

        img_id_val = img.get("id", "")
        if isinstance(img_id_val, list):
            img_id_val = " ".join(img_id_val)

        img_attrs = f"{img_class_val} {img_id_val} {alt_val} {src}"

        if positive_keywords.search(img_attrs):
            score += 20
            reasons.append("Keyword Match (logo/brand)")

        if domain_stem and domain_stem in src.lower():
            score += 20
            reasons.append(f"Filename matches domain '{domain_stem}'")

        alt = alt_val.lower()
        if "logo" in alt:
            score += 10
            reasons.append("Alt text contains 'logo'")

        if negative_keywords.search(img_attrs) or negative_keywords.search(
            parent_class_str
        ):
            score -= 50
            reasons.append("Negative Keyword (partner/client)")

        update_candidate(src, score, ", ".join(reasons))

    return candidates


if __name__ == "__main__":
    main()
