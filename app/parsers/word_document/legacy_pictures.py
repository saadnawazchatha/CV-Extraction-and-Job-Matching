"""Follow live picture references in binary Word 97-2003 files."""

from bisect import bisect_right
from io import BytesIO
from itertools import chain
import re
from string import ascii_letters, digits, punctuation
from struct import error as StructError, unpack_from

from app.parsers.OCR.reader import read_image
from .office_art import floating_images, inline_image
from .pictures import WORD_IMAGE_FORMATS

OLE_SIGNATURE = bytes.fromhex("D0CF11E0A1B11AE1")
# Positions of the named tables in the Word 97 File Information Block (MS-DOC).
CHAR_FORMATTING, PIECE_TABLE, BODY_SHAPES, HEADER_SHAPES, DRAWINGS = 12, 33, 40, 41, 50


def _picture_markers(word, clx):
    """Find inline and floating picture characters in the current text pieces."""
    pos = 0
    while pos < len(clx) and clx[pos] == 1:
        pos += 3 + unpack_from("<H", clx, pos + 1)[0]
    if pos + 5 > len(clx) or clx[pos] != 2:
        return
    length = unpack_from("<I", clx, pos + 1)[0]
    if length < 4 or (length - 4) % 12 or length > len(clx) - pos - 5:
        return
    pieces = clx[pos + 5:pos + 5 + length]
    count = (length - 4) // 12
    total_bytes = 0
    for i in range(count):
        first, last = unpack_from("<II", pieces, i * 4)
        address = unpack_from("<I", pieces, (count + 1) * 4 + i * 8 + 2)[0]
        width = 1 if address & 0x40000000 else 2
        start = (address & 0x3FFFFFFF) // (2 if width == 1 else 1)
        stop = start + (last - first) * width
        if not start <= stop <= len(word):
            raise ValueError("Invalid Word text piece.")
        total_bytes += stop - start
        if total_bytes > 192 * 1024 * 1024:
            raise ValueError("The expanded Word document is too large.")
        pattern = rb"[\x01\x08]" if width == 1 else rb"[\x01\x08]\x00"
        for match in re.finditer(pattern, word[start:stop]):
            if match.start() % width == 0:
                yield first + match.start() // width, start + match.start(), match[0][0]


def _picture_location(props):
    # A character-property record identifies the offset in Word's Data stream.
    pos = 0
    location = None
    special = binary_data = deleted = False
    while pos + 2 <= len(props):
        code = unpack_from("<H", props, pos)[0]
        pos += 2
        size = (1, 1, 2, 4, 2, 2, None, 3)[code >> 13]
        if size is None:
            if pos >= len(props):
                return None
            size = props[pos]
            pos += 1
        if pos + size > len(props):
            return None
        if code == 0x6A03:  # sprmCPicLocation
            location = unpack_from("<I", props, pos)[0]
        elif code == 0x0855:
            special = bool(props[pos])
        elif code == 0x0806:
            binary_data = bool(props[pos])
        elif code == 0x0800:
            deleted = bool(props[pos])
        pos += size
    return location if pos == len(props) and special and not binary_data and not deleted else None


def _formatting_page(block):
    if len(block) != 512:
        return
    n = block[511]
    if 4 * (n + 1) + n > 511:
        return
    for j in range(n):
        offset = 2 * block[4 * (n + 1) + j]
        if offset and offset + 1 + block[offset] <= 511:
            location = _picture_location(block[offset + 1:offset + 1 + block[offset]])
            if location is not None:
                first, last = unpack_from("<II", block, j * 4)
                yield first, last, location


def _inline_runs(word, table):
    # The active character-formatting table points to 512-byte formatting pages.
    runs = []
    count = (len(table) - 4) // 8
    decoded = {}
    for i in range(count):
        lower, upper = unpack_from("<II", table, i * 4)
        page = unpack_from("<I", table, (count + 1 + i) * 4)[0] & 0x003FFFFF
        if lower >= upper or page * 512 >= len(word):
            continue
        if page not in decoded:
            decoded[page] = list(_formatting_page(word[page * 512:(page + 1) * 512]))
        for first, last, location in decoded[page]:
            start, end = max(first, lower), min(last, upper)
            if start < end:
                runs.append((start, end, location))
    return sorted(runs)


def _shape_anchors(table, story_start):
    count = (len(table) - 4) // 30  # A character position and a 26-byte SPA per shape.
    for i in range(count):
        cp = unpack_from("<I", table, 4 * i)[0]
        shape = unpack_from("<I", table, 4 * (count + 1) + 26 * i)[0]
        yield story_start + cp, shape


def _referenced_images(ole):
    word = memoryview(ole.openstream("WordDocument").read())
    if unpack_from("<H", word, 2)[0] < 0x00C1:  # Word versions before OfficeArt
        return
    flags = unpack_from("<H", word, 10)[0]
    table_name = "1Table" if flags & 0x0200 else "0Table"
    table = memoryview(ole.openstream(table_name).read())
    sizes = 34 + 2 * unpack_from("<H", word, 32)[0]
    pairs = sizes + 4 + 4 * unpack_from("<H", word, sizes)[0]

    def section(index):
        if index >= unpack_from("<H", word, pairs - 2)[0]:
            return table[:0]
        start, size = unpack_from("<II", word, pairs + 8 * index)
        if size and start + size > len(table):
            raise ValueError("Invalid table in the Word document.")
        return table[start:start + size]

    markers = _picture_markers(word, section(PIECE_TABLE))
    first_marker = next(markers, None)
    if first_marker is None:
        return
    runs = _inline_runs(word, section(CHAR_FORMATTING))
    starts = [run[0] for run in runs]
    main_chars, footnote_chars, header_chars, macro_chars, comment_chars = unpack_from(
        "<5I", word, sizes + 2 + 3 * 4
    )
    hidden_start = main_chars + footnote_chars + header_chars
    anchors = dict(_shape_anchors(section(BODY_SHAPES), 0))
    anchors.update(_shape_anchors(section(HEADER_SHAPES), main_chars + footnote_chars))
    shapes = floating_images(section(DRAWINGS), word, set(anchors.values())) if anchors else {}
    data = memoryview(ole.openstream("Data").read()) if ole.exists("Data") else memoryview(b"")
    for cp, fc, marker in chain((first_marker,), markers):
        if hidden_start <= cp < hidden_start + macro_chars + comment_chars:
            continue
        if marker == 8:
            image = shapes.get(anchors.get(cp))
            if image is not None:
                yield fc, "floating", image
        else:
            i = bisect_right(starts, fc) - 1
            if i >= 0 and fc < runs[i][1]:
                yield fc, "inline", inline_image(data, runs[i][2], word)


def add_picture_text(content: bytes, read_native) -> str:
    native_text = read_native(content)
    if not content.startswith(OLE_SIGNATURE):
        return native_text
    try:
        import olefile
    except ImportError as error:
        raise FileNotFoundError("Legacy Word picture support needs olefile. Run python -m pip install -r requirements.txt.") from error
    try:
        temporary_copy = BytesIO(content)
        with olefile.OleFileIO(temporary_copy, write_mode=True) as document:
            pictures = list(_referenced_images(document))
            if not pictures:
                return native_text
            # Antiword gives floating shapes no position in its text output.
            # Mark those positions in a disposable copy with unused printable
            # characters. Antiword then gives us their reading order too.
            marks = ""
            if any(kind == "floating" for _, kind, _ in pictures) or native_text.count("[pic]") != len(pictures):
                available = "".join(c for c in punctuation + ascii_letters + digits if c not in native_text)
                if len(available) >= len(pictures):
                    marks = available[:len(pictures)]
                    word = bytearray(document.openstream("WordDocument").read())
                    for mark, (offset, _, _) in zip(marks, pictures):
                        word[offset] = ord(mark)
                    document.write_stream("WordDocument", bytes(word))
    except (OSError, KeyError, IndexError, StructError) as error:
        raise ValueError("Cannot read the picture references in this .doc file.") from error

    cache = {}
    texts = []
    for _, _, picture in pictures:
        text = ""
        if picture is not None:
            if picture not in cache:
                image, crop = picture
                cache[picture] = read_image(bytes(image), formats=WORD_IMAGE_FORMATS, crop=crop)
            text = cache[picture]
        texts.append(text)

    if marks:
        try:
            marked_text = read_native(temporary_copy.getvalue())
        except ValueError:
            marked_text = None  # Keep the already-read native text if the marked copy fails.
        if marked_text is not None and all(marked_text.count(mark) <= 1 for mark in marks):
            replacements = dict(zip(marks, texts))
            rendered = re.sub("[" + re.escape(marks) + "]",
                              lambda m: "\n" + replacements[m[0]] + "\n", marked_text)
            # Some older writers place pictures in stories Antiword does not print.
            missing = [text for mark, text in replacements.items() if mark not in marked_text and text]
            return "\n\n".join(filter(None, (rendered.strip(), *missing)))

    inline = [text for (_, kind, _), text in zip(pictures, texts) if kind == "inline"]
    floating = [text for (_, kind, _), text in zip(pictures, texts) if kind == "floating"]
    if inline and native_text.count("[pic]") == len(inline):
        values = iter(inline)
        native_text = re.sub(r"\[pic\]", lambda _: "\n" + next(values) + "\n", native_text)
        inline = []
    return "\n\n".join(part for part in (native_text.strip(), *inline, *floating) if part)
