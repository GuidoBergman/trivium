#!/usr/bin/env python3
"""Render PDF pages to PNG so they can actually be looked at.

Two jobs depend on this:

  the visual pass  reading worksheets, diagrams and tables whose content never
                   reaches the text layer
  the OCR audit    comparing a machine-read text layer against the page it was
                   read from, to measure how wrong it is

The rendered files are kept, not deleted, because they are the evidence behind
any figure note. A claim about a worksheet is only checkable if the reader can
open the same image the note was written from.

Usage:
  tv_pages.py <topic>/text/<slug>.map.json --pages 12,44,45,60-64 [--dpi 150]
  tv_pages.py <topic>/text/<slug>.map.json --with-images        # every figure page
  tv_pages.py <topic>/text/<slug>.map.json --sample 12          # spread for auditing
"""

import argparse
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tvlib  # noqa: E402


def parse_pages(spec):
    pages = set()
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            lo, hi = part.split("-", 1)
            pages.update(range(int(lo), int(hi) + 1))
        else:
            pages.add(int(part))
    return sorted(pages)


def evenly_spaced(total, count):
    """A spread across the whole book, not the first N pages.

    Auditing the first twelve pages of a scan measures the front matter, which
    is exactly where OCR does best and where the content matters least.
    """
    if count >= total:
        return list(range(1, total + 1))
    step = total / count
    return sorted({max(1, min(total, int(i * step) + 1)) for i in range(count)})


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("map_file")
    ap.add_argument("--pages", help="comma separated, ranges allowed: 4,12,40-44")
    ap.add_argument("--from-report", metavar="EXTRACTION_JSON",
                    help="the pages the quality gate listed for the visual pass. "
                         "Preferred over --with-images: on a scan every page is "
                         "an image, and only the gate knows which ones actually "
                         "hide content behind one.")
    ap.add_argument("--with-images", action="store_true",
                    help="every page carrying an image, ignoring provenance")
    ap.add_argument("--sample", type=int, help="N pages spread across the book")
    ap.add_argument("--dpi", type=int, default=150)
    ap.add_argument("--out", help="output directory, defaults to <topic>/pages/<slug>")
    args = ap.parse_args()

    if not os.path.exists(args.map_file):
        tvlib.die(f"no such file: {args.map_file}")
    mapping = tvlib.load_map(args.map_file)

    if mapping.get("kind") != "pdf":
        tvlib.die(f"{mapping.get('slug')} is a {mapping.get('kind')}, which has no "
                  "pages to render. Only PDFs can be rendered.")

    source = mapping.get("source")
    if not source or not os.path.exists(source):
        tvlib.die(f"the original PDF is missing: {source}")

    total = len(mapping.get("pages", []))
    if args.pages:
        pages = parse_pages(args.pages)
    elif args.from_report:
        if not os.path.exists(args.from_report):
            tvlib.die(f"no such report: {args.from_report}. Run tv_quality.py first.")
        with open(args.from_report, encoding="utf-8") as fh:
            report = json.load(fh)
        labels = set(report.get("visual_pass_pages", []))
        pages = [p["page"] for p in mapping.get("images", [])
                 if p["label"] in labels]
    elif args.with_images:
        pages = [i["page"] for i in mapping.get("images", []) if i["figure"]]
        if mapping.get("provenance", "native") != "native":
            print("warning: this book is a scan, so every page counts as an "
                  "image and all of them will be rendered. Use --from-report "
                  "to render only the pages that hide content behind one.",
                  file=sys.stderr)
    elif args.sample:
        pages = evenly_spaced(total, args.sample)
    else:
        tvlib.die("choose one of --pages, --from-report, --with-images or --sample")

    pages = [p for p in pages if 1 <= p <= total]
    if not pages:
        print("nothing to render")
        return

    text_dir = os.path.dirname(os.path.abspath(args.map_file))
    out_dir = args.out or os.path.join(os.path.dirname(text_dir), "pages",
                                       mapping["slug"])
    os.makedirs(out_dir, exist_ok=True)

    if not subprocess.run(["which", "pdftoppm"], capture_output=True).returncode == 0:
        tvlib.die("pdftoppm is not installed. Install poppler-utils.")

    written = []
    for page in pages:
        prefix = os.path.join(out_dir, f"p{page:04d}")
        target = f"{prefix}.png"
        if os.path.exists(target):
            written.append(target)
            continue
        subprocess.run(
            ["pdftoppm", "-png", "-r", str(args.dpi),
             "-f", str(page), "-l", str(page), "-singlefile", source, prefix],
            check=True, capture_output=True,
        )
        if os.path.exists(target):
            written.append(target)

    print(json.dumps({
        "slug": mapping["slug"],
        "provenance": mapping.get("provenance", "unknown"),
        "dpi": args.dpi,
        "count": len(written),
        "dir": out_dir,
        "files": written,
    }, indent=2))


if __name__ == "__main__":
    main()
