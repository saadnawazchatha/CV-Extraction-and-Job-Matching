from contextlib import closing
from io import BytesIO
from math import isfinite
from threading import Lock

import pdfplumber
import pypdfium2 as pdfium
from PIL import Image
from pdfplumber.utils.exceptions import PdfminerException
from pypdf import PageObject, PdfReader
from pypdf.errors import DependencyError, FileNotDecryptedError, PyPdfError

from app.parsers.OCR.reader import recognize

# PDFium shares state across threads, so concurrent uploads take turns rendering pages.
_render_lock = Lock()


def _render_page(content: bytes, index: int) -> Image.Image:
    with _render_lock, pdfium.PdfDocument(content, password="") as document:
        with closing(document[index]) as page:
            width, height = page.get_size()
            if not all(isfinite(side) and side > 0 for side in (width, height)):
                raise ValueError("Invalid PDF page dimensions.")
            # A PDF inch is 72 points. Aim for 300 DPI and cap the long edge to limit memory.
            scale = min(300 / 72, 3000 / max(width, height))
            with closing(page.render(scale=scale)) as bitmap:
                return bitmap.to_pil().copy()


def _append_links(page: PageObject, text: str) -> str:
    # A label such as 'Portfolio' can hide the actual URL in a link annotation.
    for reference in page.annotations or []:
        annotation = reference.get_object()
        action = annotation.get("/A") if isinstance(annotation, dict) else None
        action = action.get_object() if action is not None else None
        url = action.get("/URI") if isinstance(action, dict) else None
        if isinstance(url, str) and url and url not in text:
            text += "\n" + url
    return text.strip()


def read_pdf(content: bytes) -> str:
    try:
        document = PdfReader(BytesIO(content))
        if document.is_encrypted and not document.decrypt(""):
            raise ValueError("This PDF requires a password. Upload an unlocked copy.")

        parts = []
        with pdfplumber.open(BytesIO(content)) as pdf:
            for index, page in enumerate(pdf.pages):
                text = (page.extract_text() or "").strip()
                # OCR pages with content but no text. A CV can mix scans and selectable text.
                if not text and page.objects:
                    with _render_page(content, index) as image:
                        text = recognize(image)
                parts.append(_append_links(document.pages[index], text))
                page.close()

        # Form values can sit outside the page text. Keep them with their field names.
        for name, value in document.get_form_text_fields().items():
            if isinstance(value, str) and value.strip():
                parts.append(f"{name}: {value}")
        return "\n\n".join(filter(None, parts))
    except (DependencyError, FileNotDecryptedError) as error:
        raise ValueError("Upload an unlocked copy of this PDF.") from error
    except (PyPdfError, PdfminerException, pdfium.PdfiumError, OSError, KeyError, TypeError, IndexError) as error:
        raise ValueError("This PDF could not be read. Check that the file opens correctly.") from error
