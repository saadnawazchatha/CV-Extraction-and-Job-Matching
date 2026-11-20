from docx.opc.constants import RELATIONSHIP_TYPE as RT
from docx.oxml.ns import qn

from app.parsers.OCR.reader import IMAGE_FORMATS, read_image

BLIP = qn("a:blip")
VML_IMAGE = "{urn:schemas-microsoft-com:vml}imagedata"
ALTERNATE = "{http://schemas.openxmlformats.org/markup-compatibility/2006}AlternateContent"
WORD_TEXT = qn("w:t")
WORD_IMAGE_FORMATS = (*IMAGE_FORMATS, "GIF", "DIB")
RASTER_TYPES = {
    "image/png", "image/x-png", "image/jpeg", "image/jpg", "image/pjpeg",
    "image/gif", "image/tiff", "image/bmp", "image/x-ms-bmp", "image/dib", "image/webp",
}


def embedded_picture(part, node):
    if node.tag == BLIP:
        rel_id = node.get(qn("r:embed"))
    elif node.tag == VML_IMAGE:
        rel_id = node.get(qn("r:id")) or node.get("{urn:schemas-microsoft-com:office:office}relid")
    else:
        return None

    relation = part.rels.get(rel_id)
    if relation is None or relation.is_external or relation.reltype != RT.IMAGE:
        return None
    picture = relation.target_part
    return picture if picture.content_type.lower() in RASTER_TYPES else None


def document_nodes(part, node):
    if node.tag in (qn("w:del"), qn("w:moveFrom")):
        return
    # Word can store a drawing twice, as a preferred version and a fallback.
    if node.tag == ALTERNATE:
        for branch in node:
            if any((child.tag == WORD_TEXT and (child.text or "").strip())
                   or embedded_picture(part, child) is not None for child in branch.iter()):
                yield from document_nodes(part, branch)
                break
        return
    yield node
    for child in node:
        yield from document_nodes(part, child)


def _crop_margins(node):
    if node.tag == BLIP:
        rect = node.getparent().find(qn("a:srcRect"))
        if rect is None:
            return None
        values = [rect.get(side, "0") for side in ("l", "t", "r", "b")]
    else:
        values = [node.get("crop" + side, "0") for side in ("left", "top", "right", "bottom")]
    margins = []
    for value in values:
        if value.endswith("%"):
            fraction = float(value[:-1]) / 100
        elif value.endswith("f"):  # VML fixed-point fraction
            fraction = float(value[:-1]) / 65536
        else:
            fraction = float(value) / (100000 if node.tag == BLIP else 1)
        margins.append(fraction)
    return tuple(margins) if any(margins) else None


def picture_text(part, node, cache):
    picture = embedded_picture(part, node)
    if picture is None:
        return ""
    # The same embedded file can be displayed several times in one CV.
    crop = _crop_margins(node)
    key = (picture, crop)
    if key not in cache:
        cache[key] = read_image(picture.blob, formats=WORD_IMAGE_FORMATS, crop=crop)
    return cache[key]
