"""Read the OfficeArt picture records used by Word 97-2003."""

from struct import Struct, unpack_from
from typing import NamedTuple


class Record(NamedTuple):
    kind: int
    instance: int
    data: memoryview


# Each OfficeArt drawing record starts with flags, a type, and the byte length of its payload.
HEADER = Struct("<HHI")
RASTER_RECORDS = {0xF01D, 0xF02A, 0xF01E, 0xF01F, 0xF029}


def records(data):
    offset = 0
    while offset + HEADER.size <= len(data):
        flags, kind, length = HEADER.unpack_from(data, offset)
        offset += HEADER.size
        if length > len(data) - offset:
            return
        yield Record(kind, flags >> 4, data[offset:offset + length])
        offset += length


def _raster(record):
    if record is None or record.kind not in RASTER_RECORDS:
        return None
    # Skip one or two 16-byte identifiers and a one-byte tag to reach the image bytes.
    start = 33 if record.instance & 1 else 17
    return record.data[start:] if len(record.data) > start else None


def _stored_image(record, word):
    if record.kind != 0xF007:
        return _raster(record)
    data = record.data
    if len(data) < 36:
        return None
    # Word can store the image inside this entry or point to its bytes in the main document stream.
    nested = next(records(data[36 + data[33]:]), None)
    if nested is not None:
        return _raster(nested)
    offset = unpack_from("<I", data, 28)[0]
    return _raster(next(records(word[offset:]), None))


def _picture_properties(shape):
    props = {}
    for prop in records(shape.data):
        if prop.kind in (0xF00B, 0xF121, 0xF122):
            for i in range(min(prop.instance, len(prop.data) // 6)):
                key, value = unpack_from("<Hi", prop.data, i * 6)
                field = key & 0x3FFF
                if not (key & 0x8000) and 0x0100 <= field <= 0x0104:
                    props.setdefault(field, value)
    # Word stores crop margins in units of 1/65536 of the image dimension.
    # Return them in the left, top, right, bottom order the OCR reader expects.
    crop = tuple(props.get(k, 0) / 65536 for k in (0x0102, 0x0100, 0x0103, 0x0101))
    return props.get(0x0104, 0), crop if any(crop) else None


def inline_image(data, offset, word):
    if offset + 8 > len(data):
        return None
    length, header_size, kind = unpack_from("<IHH", data, offset)
    if header_size < 68 or not header_size <= length <= len(data) - offset:
        return None
    picture = data[offset:offset + length]
    start = header_size
    # Type 102 includes a length-prefixed name before its drawing records.
    if kind == 102 and start < length:
        start += 1 + picture[start]
    elif kind != 100:
        return None
    crop = None
    for record in records(picture[start:]):
        if record.kind == 0xF004:
            _, crop = _picture_properties(record)
            continue
        image = _stored_image(record, word)
        if image is not None:
            return image, crop
    return None


def _shape_references(drawing):
    # Walk nested groups to find image references, skipping shapes marked as deleted.
    pending = [drawing]
    while pending:
        for child in records(pending.pop().data):
            if child.kind == 0xF003:
                pending.append(child)
            elif child.kind == 0xF004:
                shape = next((r for r in records(child.data) if r.kind == 0xF00A), None)
                if shape is not None and len(shape.data) >= 8:
                    shape_id, flags = unpack_from("<II", shape.data)
                    if not flags & 8:
                        index, crop = _picture_properties(child)
                        if index:
                            yield shape_id, index, crop


def floating_images(art, word, wanted_shapes):
    group = next(records(art), None)
    if group is None or group.kind != 0xF000:
        return {}
    store = next((r for r in records(group.data) if r.kind == 0xF001), None)
    if store is None:
        return {}
    entries = list(records(store.data))
    found = {}
    pos = HEADER.size + len(group.data)
    while pos < len(art):
        drawing = next(records(art[pos + 1:]), None)
        if drawing is None:
            break
        if drawing.kind == 0xF002:
            for shape, index, crop in _shape_references(drawing):
                # Use only anchored shapes. Image-store indexes in Word start at one.
                if shape in wanted_shapes and 1 <= index <= len(entries):
                    image = _stored_image(entries[index - 1], word)
                    if image is not None:
                        found[shape] = image, crop
        pos += 1 + HEADER.size + len(drawing.data)
    return found
