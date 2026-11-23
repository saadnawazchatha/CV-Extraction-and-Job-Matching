import os
import re
import shutil
import subprocess
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import BadZipFile, ZipFile

from docx import Document
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from docx.oxml import parse_xml
from docx.oxml.ns import qn

from app.parsers.OCR.reader import OCRUnavailable
from .legacy_pictures import add_picture_text
from .pictures import BLIP, VML_IMAGE, document_nodes, picture_text

SPACING = {qn("w:p"): "\n", qn("w:br"): "\n", qn("w:cr"): "\n", qn("w:tab"): "\t"}
FIELD_LINK = re.compile(r'\bHYPERLINK\s+(?:"([^"]+)"|([^\s\\]+))', re.IGNORECASE)


def _part_text(part, image_cache) -> str:
    pieces = []
    links = []
    # Read XML in document order to keep table and picture text beside the surrounding paragraphs.
    for node in document_nodes(part, parse_xml(part.blob)):
        if node.tag == qn("w:t"):
            pieces.append(node.text or "")
        elif node.tag in SPACING:
            pieces.append(SPACING[node.tag])
        elif node.tag in (BLIP, VML_IMAGE):
            text = picture_text(part, node, image_cache)
            if text:
                pieces.extend(("\n", text, "\n"))
        elif node.tag == qn("w:hyperlink"):
            link = part.rels.get(node.get(qn("r:id")))
            if link is not None and link.is_external:
                links.append(link.target_ref)
        elif node.tag in (qn("w:fldSimple"), qn("w:instrText")):
            match = FIELD_LINK.search(node.get(qn("w:instr")) or node.text or "")
            if match:
                links.append(match[1] or match[2])
    text = "".join(pieces).strip()
    # A link labeled 'LinkedIn' can hide the address. Append each target that the visible text omits.
    return "\n".join([text] + [url for url in dict.fromkeys(links) if url not in text]).strip()


def read_docx(content: bytes) -> str:
    try:
        # A .docx is a ZIP archive. Check its expanded size before opening the XML and embedded pictures.
        with ZipFile(BytesIO(content)) as archive:
            if sum(item.file_size for item in archive.infolist()) > 192 * 1024 * 1024:
                raise ValueError("The expanded Word document is too large.")
        body = Document(BytesIO(content)).part
        related = body.rels.values()
        # Contact details often sit in headers or footers. Include those parts as well as the body and notes.
        parts = [r.target_part for r in related if r.reltype == RT.HEADER]
        parts.append(body)
        parts.extend(
            r.target_part
            for r in related
            if r.reltype in (RT.FOOTNOTES, RT.ENDNOTES, RT.FOOTER)
        )
        image_cache = {}
        # Sections can share a header or footer. Read each part once to avoid repeating its text.
        texts = (_part_text(part, image_cache) for part in dict.fromkeys(parts))
        return "\n\n".join(filter(None, texts))
    except OCRUnavailable:
        raise
    except (BadZipFile, KeyError, OSError, RuntimeError, SyntaxError) as error:
        raise ValueError("This .docx file is damaged or password-protected.") from error


def read_doc(content: bytes) -> str:
    # Look for Antiword on PATH, then in Git for Windows, to read the older binary .doc format.
    git_dir = Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Git" / "mingw64"
    tool = Path(shutil.which("antiword") or git_dir / "bin" / "antiword.exe")
    if not tool.is_file():
        raise FileNotFoundError("Legacy .doc files need Antiword. You can also save the file as .docx.")
    env = os.environ.copy()
    maps = tool.resolve().parents[1] / "share" / "antiword"
    if (maps / "UTF-8.txt").is_file():
        env["ANTIWORDHOME"] = str(maps)
    with TemporaryDirectory() as folder:
        path = Path(folder) / "input.doc"

        # Antiword needs a file path. Reuse it for the original and any marked copy
        # the picture reader needs to place OCR text beside the right paragraph.
        def read_native(data):
            path.write_bytes(data)
            try:
                result = subprocess.run(
                    [str(tool), "-t", "-w", "0", "-m", "UTF-8.txt", str(path)],
                    env=env,
                    capture_output=True,
                    timeout=45,
                    check=True,
                )
            except (subprocess.SubprocessError, OSError) as error:
                raise ValueError("Antiword could not read this .doc file. Try an unlocked .docx copy.") from error
            return result.stdout.decode("utf-8").replace("\r\n", "\n").strip()

        return add_picture_text(content, read_native)
