#!/usr/bin/env python3
"""
Unpack a Claude Design bundled HTML export into editable source.

Claude Design exports a single HTML file in which the whole page is stored as a
JSON-encoded string inside a <script type="__bundler/template"> tag, with fonts
held separately in a __bundler/manifest tag and images inlined as base64 data
URIs. That format works in a browser but is unusable as source: the page is one
enormous line, and every '</' inside it is escaped as '<\\u002F', so ordinary
find-and-replace corrupts it.

This script turns that bundle back into:

    index.html          normal, multi-line, hand-editable HTML
    assets/fonts/*.woff2
    assets/images/*

Usage:
    python3 tools/unbundle.py <bundle.html> [output-dir]

Re-run it after any fresh Claude Design export to refresh the repo.
"""

import base64
import gzip
import hashlib
import json
import pathlib
import re
import sys

# Images are named from their alt text so files are recognisable in the repo.
IMAGE_NAMES = [
    ("Narsapur Christian Hospital Logo", "logo"),
    ("Dr. Philip Mitta",                 "doctors/philip-mitta"),
    ("Dr. Kalyani Thomas",               "doctors/kalyani-thomas"),
    ("Dr. Sunayana Kamala",              "doctors/sunayana-kamala"),
    ("Dr. Smita Mitta",                  "doctors/smita-mitta"),
    ("Dr. Surya Sandeep",                "doctors/surya-sandeep"),
    ("Dr. Kesia Giju George",            "doctors/kesia-giju-george"),
    ("Group photo",                      "staff-group"),
    ("Google Business Profile QR",       "google-business-qr"),
]

EXT = {"jpeg": "jpg", "svg+xml": "svg"}


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def read_bundle(path):
    html = pathlib.Path(path).read_text(encoding="utf-8")

    def section(name):
        m = re.search(rf'<script type="__bundler/{name}">(.*?)</script>', html, re.S)
        if not m:
            raise SystemExit(f"error: no __bundler/{name} section — is this a Claude Design bundle?")
        return json.loads(m.group(1).strip())

    return section("template"), section("manifest")


def name_image(alt, index):
    for needle, name in IMAGE_NAMES:
        if needle.lower() in alt.lower():
            return name
    return f"image-{index:02d}"


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)

    bundle = sys.argv[1]
    out = pathlib.Path(sys.argv[2] if len(sys.argv) > 2 else ".")
    fonts_dir = out / "assets" / "fonts"
    images_dir = out / "assets" / "images"
    fonts_dir.mkdir(parents=True, exist_ok=True)
    images_dir.mkdir(parents=True, exist_ok=True)

    page, manifest = read_bundle(bundle)
    original_len = len(page)

    # ---- fonts -------------------------------------------------------------
    # Each @font-face is preceded by a comment naming its unicode subset, e.g.
    #   /* latin */
    #   @font-face { font-family:'Lora'; font-style:italic; font-weight:400;
    #                src: url("<uuid>") format('woff2'); }
    faces = {}
    for m in re.finditer(
        r"/\*\s*([a-z0-9\-\[\]]+)\s*\*/\s*@font-face\s*\{(.*?)\}", page, re.S | re.I
    ):
        subset, body = m.group(1), m.group(2)
        uuid = re.search(r'url\("([^"]+)"\)', body)
        if not uuid:
            continue
        fam = re.search(r"font-family:\s*'([^']+)'", body)
        sty = re.search(r"font-style:\s*(\w+)", body)
        wgt = re.search(r"font-weight:\s*(\d+)", body)
        parts = [
            slug(fam.group(1)) if fam else "font",
            (sty.group(1) if sty else "normal"),
            (wgt.group(1) if wgt else "400"),
            slug(subset),
        ]
        faces[uuid.group(1)] = "-".join(parts)

    seen, font_count = {}, 0
    for uuid, entry in manifest.items():
        data = base64.b64decode(entry["data"])
        if entry.get("compressed"):
            try:
                data = gzip.decompress(data)
            except OSError:
                pass
        digest = hashlib.sha256(data).hexdigest()
        if digest in seen:                       # identical file already written
            filename = seen[digest]
        else:
            stem = faces.get(uuid, f"font-{uuid[:8]}")
            filename = f"{stem}.woff2"
            n, base_stem = 2, stem
            while (fonts_dir / filename).exists():   # name collision, not content
                filename = f"{base_stem}-{n}.woff2"
                n += 1
            (fonts_dir / filename).write_bytes(data)
            seen[digest] = filename
            font_count += 1
        page = page.replace(f'url("{uuid}")', f'url("assets/fonts/{filename}")')

    # ---- images ------------------------------------------------------------
    img_seen, img_count, idx = {}, 0, 0
    def replace_image(m):
        nonlocal img_count, idx
        idx += 1
        mime, b64 = m.group(1), m.group(2)
        data = base64.b64decode(b64)
        digest = hashlib.sha256(data).hexdigest()
        if digest in img_seen:
            return img_seen[digest]
        alt = re.search(r'alt="([^"]*)"', page[m.end(): m.end() + 500])
        stem = name_image(alt.group(1) if alt else "", idx)
        rel = f"assets/images/{stem}.{EXT.get(mime, mime)}"
        target = images_dir.parent.parent / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        img_seen[digest] = rel
        img_count += 1
        return rel

    page = re.sub(r"data:image/([a-z+]+);base64,([A-Za-z0-9+/=]+)", replace_image, page)

    # ---- write page --------------------------------------------------------
    (out / "index.html").write_text(page, encoding="utf-8")

    # ---- verify ------------------------------------------------------------
    problems = []
    if re.search(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", page):
        problems.append("unresolved bundler UUID still in page")
    if "data:image/" in page:
        problems.append("base64 image still inline")
    for ref in set(re.findall(r'(?:src|url\()"?(assets/[^"\')]+)', page)):
        if not (out / ref).exists():
            problems.append(f"missing referenced file: {ref}")

    print(f"index.html      {original_len:>9,} -> {len(page):,} chars")
    print(f"fonts written   {font_count}")
    print(f"images written  {img_count}")
    if problems:
        print("\nPROBLEMS:")
        for p in problems:
            print("  -", p)
        sys.exit(1)
    print("\nAll references resolve.")


if __name__ == "__main__":
    main()
