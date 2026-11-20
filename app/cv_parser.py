"""Read an uploaded CV using the reader for its file format."""

from pathlib import PureWindowsPath

from fastapi import HTTPException, UploadFile

from .parsers.OCR.reader import IMAGE_FORMATS, OCRUnavailable, read_image
from .parsers.pdf.reader import read_pdf
from .parsers.word_document.reader import read_doc, read_docx


READERS = {".doc": read_doc, ".docx": read_docx, ".pdf": read_pdf}
for extensions in IMAGE_FORMATS.values():
    READERS.update({extension: read_image for extension in extensions})

MAX_UPLOAD_BYTES = 32 * 1024 * 1024


def parse_cv(file: UploadFile) -> tuple[str, str]:
    """Return the original filename (without its path) and the readable text."""
    name = PureWindowsPath(file.filename or "").name
    reader = READERS.get(PureWindowsPath(name).suffix.lower())
    if reader is None:
        raise HTTPException(415, f"Supported file types: {', '.join(READERS)}.")

    content = file.file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "This file exceeds 32 MiB.")
    try:
        raw_text = reader(content)
    except (FileNotFoundError, OCRUnavailable) as error:
        raise HTTPException(503, str(error)) from error
    except ValueError as error:
        raise HTTPException(422, str(error)) from error
    if not raw_text.strip():
        raise HTTPException(422, "No readable text was found in this file.")
    return name, raw_text
