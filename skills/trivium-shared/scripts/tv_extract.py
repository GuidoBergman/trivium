#!/usr/bin/env python3
"""Extract a PDF, EPUB or AZW3 into Trivium's text layout.

Writes two files next to each other:

  text/<slug>.txt       plain text, no markers, this is what quotes match against
  text/<slug>.map.json  page and chapter offsets into that text

Keeping markers out of the text file matters: a quote that spans a page break
would otherwise contain a marker and fail verification for no good reason.

The map also records two things the rest of Trivium needs in order to be honest
about what it did not read:

  provenance  "native" when the text came from the publisher's own text layer,
              "ocr" when it was machine-read off a scan. An OCR text layer means
              a verified quote proves the quote is in someone's transcription of
              the book, which is a weaker claim than being in the book.
  images      which pages carry figures. Their contents are invisible to text
              extraction, so a page whose argument lives in a diagram produces
              notes that silently omit it unless something flags the page.

Usage:
  tv_extract.py <source.pdf|.epub|.azw3> --out <topic>/text [--slug name]
"""

import argparse
import html.parser
import json
import os
import re
import subprocess
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tvlib  # noqa: E402


def slugify(name):
    stem = os.path.splitext(os.path.basename(name))[0]
    slug = re.sub(r"[^a-z0-9]+", "-", stem.lower()).strip("-")
    return slug or "book"


# --------------------------------------------------------------------------
# PDF
# --------------------------------------------------------------------------

def extract_pdf(path):
    """Return (text, pages) where pages is a list of per-page strings."""
    raw = None
    try:
        result = subprocess.run(
            ["pdftotext", "-q", "-enc", "UTF-8", path, "-"],
            capture_output=True, check=True,
        )
        raw = result.stdout.decode("utf-8", errors="replace")
    except (FileNotFoundError, subprocess.CalledProcessError):
        raw = None

    if raw is not None and raw.strip():
        # pdftotext separates pages with a form feed.
        return raw, raw.split("\f")

    try:
        import pypdf
    except ImportError:
        tvlib.die(
            "no PDF extractor available. Install poppler-utils (pdftotext) "
            "or the pypdf Python package."
        )

    reader = pypdf.PdfReader(path)
    pages = [(page.extract_text() or "") for page in reader.pages]
    return "\f".join(pages), pages


def pdf_chapters(path, page_spans):
    """Chapter spans from the PDF outline, or [] when there is no outline."""
    try:
        import pypdf
    except ImportError:
        return []

    try:
        reader = pypdf.PdfReader(path)
        outline = reader.outline
    except Exception:
        return []

    entries = []

    def walk(items, depth=0):
        for item in items:
            if isinstance(item, list):
                walk(item, depth + 1)
                continue
            if depth > 0:
                continue  # top-level entries only, deeper ones are sections
            try:
                page_no = reader.get_destination_page_number(item)
                if page_no is None:
                    continue
                entries.append((page_no, str(item.title).strip()))
            except Exception:
                continue

    try:
        walk(outline)
    except Exception:
        return []

    entries = [e for e in entries if e[1]]
    entries.sort(key=lambda e: e[0])

    chapters = []
    for i, (page_no, title) in enumerate(entries):
        if page_no >= len(page_spans):
            continue
        start = page_spans[page_no]["start"]
        if i + 1 < len(entries) and entries[i + 1][0] < len(page_spans):
            end = page_spans[entries[i + 1][0]]["start"]
        else:
            end = page_spans[-1]["end"]
        if end <= start:
            continue
        chapters.append({"label": f"ch{len(chapters) + 1}", "title": title,
                         "start": start, "end": end})
    return chapters


def pdf_images(path, page_spans):
    """Per-page image inventory via pdfimages, or [] when it is unavailable.

    A page whose only image is a small logo is not interesting. A page carrying a
    worksheet, a diagram or a scan of itself is, because none of its content
    reaches the text layer.
    """
    try:
        result = subprocess.run(["pdfimages", "-list", path],
                                capture_output=True, check=True)
    except (FileNotFoundError, subprocess.CalledProcessError):
        return []

    by_page = {}
    # Columns: page num type width height color comp bpc enc interp object ID ...
    for line in result.stdout.decode("utf-8", errors="replace").splitlines()[2:]:
        parts = line.split()
        if len(parts) < 5:
            continue
        try:
            page, width, height = int(parts[0]), int(parts[3]), int(parts[4])
        except ValueError:
            continue
        if parts[2] == "smask":
            continue  # a transparency mask, not a separate picture
        entry = by_page.setdefault(page, {"count": 0, "max_w": 0, "max_h": 0})
        entry["count"] += 1
        entry["max_w"] = max(entry["max_w"], width)
        entry["max_h"] = max(entry["max_h"], height)

    inventory = []
    for page in sorted(by_page):
        if page > len(page_spans):
            continue
        entry = by_page[page]
        # Two different questions, two different thresholds.
        # figure:    big enough to carry content a reader would need to see,
        #            which is what the visual pass goes looking for.
        # full_page: the size of a scan of the whole page, which is what says
        #            this file is a photograph of a book rather than a book.
        figure = entry["max_w"] >= 200 and entry["max_h"] >= 200
        full_page = entry["max_w"] >= 700 and entry["max_h"] >= 900
        inventory.append({
            "page": page,
            "label": page_spans[page - 1]["label"],
            "count": entry["count"],
            "largest": [entry["max_w"], entry["max_h"]],
            "figure": figure,
            "full_page": full_page,
        })
    return inventory


SCANNER_MARKERS = ("internet archive", "scribe", "abbyy", "finereader",
                   "tesseract", "ocrmypdf", "scansnap", "kofax", "readiris")


def pdf_provenance(path, text, page_spans, images):
    """Decide whether the text layer is the publisher's or a machine's.

    Metadata is believed when it names a scanner or OCR engine. Otherwise the
    shape of the file decides: a scan is a full-page image on nearly every page,
    with a thin text layer sitting on top of it.
    """
    evidence = []

    try:
        info = subprocess.run(["pdfinfo", path], capture_output=True,
                              check=True).stdout.decode("utf-8", "replace").lower()
        for marker in SCANNER_MARKERS:
            if marker in info:
                evidence.append(f"metadata names {marker}")
                return "ocr", evidence
    except (FileNotFoundError, subprocess.CalledProcessError):
        pass

    pages = len(page_spans) or 1
    full_page = sum(1 for i in images if i["full_page"])
    density = len(text) / pages
    ratio = full_page / pages

    if ratio >= 0.8 and density < 2500:
        evidence.append(f"{ratio:.0%} of pages carry a full-page image")
        evidence.append(f"only {density:.0f} characters per page")
        return "ocr-suspected", evidence

    return "native", evidence


# --------------------------------------------------------------------------
# EPUB and AZW3
# --------------------------------------------------------------------------

class _Stripper(html.parser.HTMLParser):
    SKIP = {"script", "style", "head"}
    BLOCK = {"p", "div", "br", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6",
             "section", "article", "blockquote"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.chunks = []
        self.skipping = 0
        self.headings = []
        self._in_heading = False

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self.skipping += 1
        if tag in self.BLOCK:
            self.chunks.append("\n")
        if tag in ("h1", "h2", "h3") and len(self.headings) < 3:
            self._in_heading = True

    def handle_endtag(self, tag):
        if tag in self.SKIP and self.skipping:
            self.skipping -= 1
        if tag in self.BLOCK:
            self.chunks.append("\n")
        if tag in ("h1", "h2", "h3"):
            self._in_heading = False

    def handle_data(self, data):
        if self.skipping:
            return
        self.chunks.append(data)
        if self._in_heading and data.strip() and len(self.headings) < 3:
            self.headings.append(data.strip())

    @property
    def title(self):
        """Chapter titles are often split, with the number in one heading and
        the name in the next. Join them rather than reporting a chapter called
        "7"."""
        if not self.headings:
            return None
        title = self.headings[0]
        if len(title) <= 4 and len(self.headings) > 1:
            title = f"{title}. {self.headings[1]}"
        return title[:120]

    def text(self):
        joined = "".join(self.chunks)
        joined = re.sub(r"[ \t\r\f\v]+", " ", joined)
        joined = re.sub(r"\n\s*\n\s*\n+", "\n\n", joined)
        return joined.strip()


def extract_epub(path):
    """Return (text, chapters) reading the spine in reading order."""
    with zipfile.ZipFile(path) as zf:
        names = zf.namelist()

        opf_name = next((n for n in names if n.lower().endswith(".opf")), None)
        if opf_name is None:
            tvlib.die("EPUB has no .opf package file, cannot determine reading order")

        opf = zf.read(opf_name).decode("utf-8", errors="replace")
        base = os.path.dirname(opf_name)

        manifest = dict(
            re.findall(r'<item\b[^>]*?id="([^"]+)"[^>]*?href="([^"]+)"', opf)
        ) or dict(
            (i, h) for h, i in
            re.findall(r'<item\b[^>]*?href="([^"]+)"[^>]*?id="([^"]+)"', opf)
        )
        spine = re.findall(r'<itemref\b[^>]*?idref="([^"]+)"', opf)

        ordered = []
        for idref in spine:
            href = manifest.get(idref)
            if not href:
                continue
            full = os.path.normpath(os.path.join(base, href)).replace(os.sep, "/")
            if full in names:
                ordered.append(full)

        if not ordered:
            ordered = sorted(n for n in names
                             if n.lower().endswith((".xhtml", ".html", ".htm")))

        parts, chapters, cursor = [], [], 0
        for item in ordered:
            parser = _Stripper()
            try:
                parser.feed(zf.read(item).decode("utf-8", errors="replace"))
            except Exception:
                continue
            body = parser.text()
            if len(body) < 20:
                continue
            block = body + "\n\n"
            parts.append(block)
            chapters.append({
                "label": f"ch{len(chapters) + 1}",
                "title": parser.title or os.path.basename(item),
                "source": item,
                "start": cursor,
                "end": cursor + len(block),
            })
            cursor += len(block)

    return "".join(parts), chapters


def extract_kf8(path):
    """Return (text, chapters) for an AZW3 or MOBI file.

    KF8 concatenates the book's XHTML files into one blob, so each <body> is one
    original document and makes the same chapter unit an EPUB spine item does.
    """
    import tv_kf8

    try:
        rawml = tv_kf8.read_rawml(path)
    except tv_kf8.Kf8Error as exc:
        tvlib.die(str(exc))

    # KF8 stores a skeleton of empty <body> stubs with each document's real text
    # appended after its stub, to be stitched back together by the reader. So the
    # section boundary is where one <body> starts, not where it closes. Pairing
    # the tags yields 38 empty strings and no book.
    starts = [m.start() for m in re.finditer(r"<body\b", rawml, re.I)]
    if starts:
        bounds = starts + [len(rawml)]
        sections = [rawml[bounds[i]:bounds[i + 1]] for i in range(len(starts))]
    else:
        sections = [rawml]

    parts, chapters, cursor = [], [], 0
    for section in sections:
        parser = _Stripper()
        try:
            parser.feed(section)
        except Exception:
            continue
        body = parser.text()
        if len(body) < 20:
            continue
        block = body + "\n\n"
        parts.append(block)
        chapters.append({
            "label": f"ch{len(chapters) + 1}",
            "title": parser.title or f"section {len(chapters) + 1}",
            "start": cursor,
            "end": cursor + len(block),
        })
        cursor += len(block)

    return "".join(parts), chapters


# --------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("source")
    ap.add_argument("--out", required=True, help="output text/ directory")
    ap.add_argument("--slug", help="book slug, defaults to a slug of the filename")
    args = ap.parse_args()

    if not os.path.exists(args.source):
        tvlib.die(f"no such file: {args.source}")

    slug = args.slug or slugify(args.source)
    os.makedirs(args.out, exist_ok=True)
    ext = os.path.splitext(args.source)[1].lower()

    if ext == ".pdf":
        text, pages = extract_pdf(args.source)
        text = text.replace("\f", "\n")
        spans, cursor = [], 0
        for i, page in enumerate(pages, 1):
            length = len(page) + 1  # the form feed we replaced with a newline
            spans.append({"label": f"p.{i}", "start": cursor,
                          "end": min(cursor + length, len(text))})
            cursor += length
        images = pdf_images(args.source, spans)
        provenance, evidence = pdf_provenance(args.source, text, spans, images)
        mapping = {
            "kind": "pdf", "slug": slug,
            "source": os.path.abspath(args.source),
            "total_chars": len(text),
            "provenance": provenance,
            "provenance_evidence": evidence,
            "pages": spans,
            "chapters": pdf_chapters(args.source, spans),
            "images": images,
        }
    elif ext in (".epub", ".azw3", ".azw", ".mobi", ".prc"):
        if ext == ".epub":
            text, chapters = extract_epub(args.source)
            kind = "epub"
        else:
            text, chapters = extract_kf8(args.source)
            kind = "azw3"
        mapping = {
            "kind": kind, "slug": slug,
            "source": os.path.abspath(args.source),
            "total_chars": len(text),
            # Reflowable formats carry the publisher's own text. Images exist but
            # cannot be tied to a page, so figure handling is PDF-only for now.
            "provenance": "native",
            "provenance_evidence": [],
            "pages": [],
            "chapters": chapters,
            "images": [],
        }
    else:
        tvlib.die(f"unsupported format {ext!r}, expected .pdf, .epub or .azw3")

    txt_path = os.path.join(args.out, f"{slug}.txt")
    map_path = os.path.join(args.out, f"{slug}.map.json")
    with open(txt_path, "w", encoding="utf-8") as fh:
        fh.write(text)
    with open(map_path, "w", encoding="utf-8") as fh:
        json.dump(mapping, fh, indent=2, ensure_ascii=False)

    print(json.dumps({
        "slug": slug,
        "text": txt_path,
        "map": map_path,
        "chars": len(text),
        "pages": len(mapping["pages"]),
        "chapters": len(mapping["chapters"]),
        "provenance": mapping["provenance"],
        "provenance_evidence": mapping["provenance_evidence"],
        "pages_with_figures": sum(1 for i in mapping["images"] if i["figure"]),
        "pages_full_page_image": sum(1 for i in mapping["images"] if i["full_page"]),
    }, indent=2))

    if mapping["provenance"] != "native":
        print("\nNOTE: this text layer was machine-read, not published as text. "
              "Record that in the brief, and audit a sample of pages against the "
              "page images before trusting fine detail such as numbers.",
              file=sys.stderr)

    if len(text.strip()) < 500:
        print("\nWARNING: almost no text extracted. This is probably an "
              "image-only PDF, which is out of scope. Do not study it.",
              file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
