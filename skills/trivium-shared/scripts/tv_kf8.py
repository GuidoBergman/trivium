"""Read AZW3 / KF8 (Kindle) files without Calibre or any third-party package.

An AZW3 is a PalmDB container. Record 0 holds a PalmDOC header followed by a MOBI
header; the records after it hold the book's XHTML, compressed with PalmDOC LZ77
and optionally carrying trailing index data that must be trimmed before
decompressing.

DRM'd files are refused rather than mangled: the encryption flag in the PalmDOC
header says so plainly, and there is no legitimate way past it.

Only the pieces Trivium needs are implemented. HUFF/CDIC compression, used by some
older MOBI files, is detected and reported rather than half-supported.
"""

import struct


class Kf8Error(Exception):
    pass


def _records(raw):
    if len(raw) < 78 or raw[60:68] != b"BOOKMOBI":
        raise Kf8Error("not a MOBI/AZW3 file (missing BOOKMOBI signature)")
    count = struct.unpack(">H", raw[76:78])[0]
    if count < 2:
        raise Kf8Error("file contains no text records")
    offsets = [struct.unpack(">I", raw[78 + 8 * i:82 + 8 * i])[0]
               for i in range(count)]
    offsets.append(len(raw))
    return [raw[offsets[i]:offsets[i + 1]] for i in range(count)]


def _trailing_size(data):
    """Size of the last trailing data entry, stored as a backwards varint."""
    size = 0
    for byte in data[-4:]:
        if byte & 0x80:
            size = 0
        size = (size << 7) | (byte & 0x7F)
    return size


def _strip_trailing(data, flags):
    """Remove index and overlap bytes appended after the compressed payload."""
    for bit in range(15, 0, -1):
        if flags & (1 << bit):
            size = _trailing_size(data)
            if 0 < size <= len(data):
                data = data[:-size]
    if flags & 1 and data:
        # Bit 0 is the multibyte-character overlap, whose length lives in the
        # bottom two bits of the final byte.
        overlap = (data[-1] & 0x3) + 1
        if overlap <= len(data):
            data = data[:-overlap]
    return data


def _palmdoc_decompress(data):
    out = bytearray()
    i, end = 0, len(data)
    while i < end:
        byte = data[i]
        i += 1
        if byte == 0:
            out.append(0)
        elif byte <= 8:
            out.extend(data[i:i + byte])
            i += byte
        elif byte <= 0x7F:
            out.append(byte)
        elif byte <= 0xBF:
            if i >= end:
                break
            pair = (byte << 8) | data[i]
            i += 1
            distance = (pair & 0x3FFF) >> 3
            length = (pair & 0x7) + 3
            if distance == 0 or distance > len(out):
                break
            for _ in range(length):
                out.append(out[-distance])
        else:
            out.append(0x20)
            out.append(byte ^ 0x80)
    return bytes(out)


def read_rawml(path):
    """Return the book's raw XHTML as a string.

    Raises Kf8Error for DRM, unsupported compression, or a malformed container.
    """
    with open(path, "rb") as fh:
        raw = fh.read()

    records = _records(raw)
    header = records[0]
    if len(header) < 16:
        raise Kf8Error("truncated PalmDOC header")

    compression, _, _text_len, text_records, _rec_size, encryption = \
        struct.unpack(">HHIHHH", header[:14])

    if encryption:
        raise Kf8Error(
            "this file is DRM protected. Trivium cannot read it, and removing "
            "the protection is not something it will do. Use a DRM-free copy."
        )
    if compression == 17480:
        raise Kf8Error(
            "HUFF/CDIC compressed MOBI, which is not supported. Convert the "
            "file to EPUB first, for example with Calibre's ebook-convert."
        )
    if compression not in (1, 2):
        raise Kf8Error(f"unknown compression method {compression}")

    encoding = "utf-8"
    if header[16:20] == b"MOBI" and len(header) >= 32:
        codepage = struct.unpack(">I", header[28:32])[0]
        encoding = {65001: "utf-8", 1252: "cp1252"}.get(codepage, "utf-8")

    flags = 0
    if len(header) >= 244:
        flags = struct.unpack(">H", header[242:244])[0]

    text_records = min(text_records, len(records) - 1)
    chunks = []
    for i in range(1, text_records + 1):
        data = _strip_trailing(records[i], flags)
        chunks.append(_palmdoc_decompress(data) if compression == 2 else data)

    rawml = b"".join(chunks).decode(encoding, errors="replace")
    if len(rawml.strip()) < 500:
        raise Kf8Error("decompressed to almost nothing, the file may be damaged")
    return rawml
