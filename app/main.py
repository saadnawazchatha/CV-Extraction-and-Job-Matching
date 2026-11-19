from pathlib import PureWindowsPath

from fastapi import FastAPI, HTTPException, UploadFile

from app.parsers.OCR.reader import IMAGE_FORMATS, OCRUnavailable, read_image
from app.parsers.pdf.reader import read_pdf
from app.parsers.word_document.reader import read_doc, read_docx

app = FastAPI(title="CV text reader", docs_url=None, redoc_url=None)
READERS = {".doc": read_doc, ".docx": read_docx, ".pdf": read_pdf}
for extensions in IMAGE_FORMATS.values():
    READERS.update({extension: read_image for extension in extensions})


@app.post("/cv/raw")
def read_cv(file: UploadFile) -> dict[str, str]:
    name = PureWindowsPath(file.filename or "").name
    reader = READERS.get(PureWindowsPath(name).suffix.lower())
    if reader is None:
        raise HTTPException(415, f"Supported file types: {', '.join(READERS)}.")

    limit = 32 * 1024 * 1024
    content = file.file.read(limit + 1)
    if len(content) > limit:
        raise HTTPException(413, "This file exceeds 32 MiB.")
    try:
        text = reader(content)
    except (FileNotFoundError, OCRUnavailable) as error:
        raise HTTPException(503, str(error)) from error
    except ValueError as error:
        raise HTTPException(422, str(error)) from error
    if not text.strip():
        raise HTTPException(422, "No readable text was found in this file.")
    return {"file_name": name, "data": text}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
