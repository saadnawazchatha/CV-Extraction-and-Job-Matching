import json
from contextlib import closing, contextmanager
from itertools import chain
from pathlib import Path
from tempfile import TemporaryDirectory

from filelock import FileLock, Timeout
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font
from openpyxl.worksheet.hyperlink import Hyperlink

ROOT = Path(__file__).resolve().parent
RAW_FILE = ROOT / "raw data.xlsx"
INFO_FILE = ROOT / "information.xlsx"
RANKING_FILE = ROOT / "ranking.xlsx"
LEGACY_FILE = ROOT / "output.xlsx"

RAW_HEADERS = ("File name", "Raw text")
INFO_HEADERS = ("File name", "Information")
# Keep these seven columns in their original positions in existing ranking reports.
RANK_HEADERS = ("Job description", "File name", "CV JSON", "Education score",
                "Experience score", "Skills score", "Overall score")
SCORE_FIELDS = ("education_score", "experience_score", "skills_score", "overall_score")

_XML_ESCAPES = {
    code: f"\\u{code:04x}"
    for code in chain(range(9), (11, 12), range(14, 32), range(0xD800, 0xE000), (0xFFFE, 0xFFFF))
}


def _cell_parts(text):
    """Split without losing a character or exceeding Excel's UTF-16 or line-feed limits."""
    start = units = breaks = 0
    for i, char in enumerate(text):
        width = 2 if ord(char) > 65535 else 1
        if units + width > 32767 or (char == "\n" and breaks == 253):
            yield text[start:i]
            start, units, breaks = i, 0, 0
        units += width
        breaks += char == "\n"
    yield text[start:]


@contextmanager
def _edit_book(path):
    try:
        with FileLock(str(path) + ".lock", timeout=5):
            book = load_workbook(path, rich_text=True) if path.exists() else Workbook()
            with closing(book):
                yield book
                with TemporaryDirectory(dir=path.parent) as tmp:
                    saved = Path(tmp) / path.name
                    book.save(saved)
                    saved.replace(path)
    except (PermissionError, Timeout) as error:
        raise OSError(f"Close {path.name} and retry the save.") from error


def _header(sheet, column, label, width):
    cell = sheet.cell(1, column, label)
    cell.font = Font(bold=True)
    sheet.column_dimensions[cell.column_letter].width = width


def _sheet(book, title, headers, widths):
    sheet = book[title] if title in book.sheetnames else book.active
    if sheet.max_row == 1 and all(cell.value is None for cell in sheet[1]):
        if sheet.title != title and len(book.worksheets) > 1:
            raise ValueError(f"Cannot identify the {title} sheet in this workbook.")
        sheet.title = title
        for column, (label, width) in enumerate(zip(headers, widths, strict=True), 1):
            _header(sheet, column, label, width)
        sheet.freeze_panes = "A2"
    elif tuple(cell.value for cell in sheet[1][:len(headers)]) != headers:
        raise ValueError(f"The {title} sheet needs these headers: {', '.join(headers)}.")
    return sheet


def _text_cell(sheet, row, column, text):
    cell = sheet.cell(row, column, text)
    cell.data_type = "s"  # CV content beginning with '=' is literal text.
    cell.alignment = Alignment(wrap_text=True, vertical="top")
    return cell


def _append_value(path, title, headers, file_name, value):
    with _edit_book(path) as book:
        sheet = _sheet(book, title, headers, (36, 100))
        start = sheet.max_row + 1
        name = file_name.translate(_XML_ESCAPES)
        if not name.strip() or next(_cell_parts(name)) != name:
            raise ValueError("The filename must fit in one nonempty Excel cell.")
        _text_cell(sheet, start, 1, name)
        # Only the first row carries a filename. Two CVs with the same name stay distinct.
        for row, part in enumerate(_cell_parts(value.translate(_XML_ESCAPES)), start):
            _text_cell(sheet, row, 2, part)


def append_raw(file_name, raw_text, path=RAW_FILE):
    _append_value(path, "Raw data", RAW_HEADERS, file_name, raw_text)


def append_information(file_name, extracted_data, path=INFO_FILE):
    value = json.dumps(extracted_data, ensure_ascii=False, indent=2)
    _append_value(path, "Information", INFO_HEADERS, file_name, value)


def _saved_record(row, name, raw_text=None, json_text=None):
    record = {"file_name": name}
    if raw_text is not None:
        record["raw_text"] = raw_text
    if json_text is not None:
        try:
            fields = json.loads(json_text)
        except (TypeError, ValueError) as error:
            raise ValueError(f"Invalid JSON for {name} at row {row}.") from error
        if not isinstance(fields, dict):
            raise ValueError(f"Expected a CV JSON object for {name} at row {row}.")
        record["extracted_data"] = fields
    return row, record


def _stage_records(rows, field):
    start, name, parts = 0, None, []
    for number, row in enumerate(rows, 2):
        new_name, chunk = row[:2]
        if new_name is not None:
            if name is not None:
                yield _saved_record(start, name, **{field: "".join(parts)})
            start, name, parts = number, str(new_name), []
        if chunk is not None:
            if name is None:
                raise ValueError(f"Missing filename before the value at row {number}.")
            parts.append(str(chunk))
    if name is not None:
        yield _saved_record(start, name, **{field: "".join(parts)})


def _legacy_raw_continues(previous, chunk):
    if not previous or not chunk:
        return False
    units = len(previous.encode("utf-16-le")) // 2
    return units + (2 if ord(chunk[0]) > 65535 else 1) > 32767 or (
        chunk.startswith("\n") and previous.count("\n") == 253
    )


def _legacy_records(rows, json_column):
    # The old writer repeated the filename on every continuation row, including raw-only rows.
    start, name, raw, details = 0, None, [], []
    incomplete_json = False
    for number, row in enumerate(rows, 2):
        new_name = row[0]
        if new_name is None:
            continue
        text = str(row[1] or "")
        piece = str(row[json_column] or "") if json_column is not None else ""
        continuation = new_name == name and (
            incomplete_json or (not piece and raw and _legacy_raw_continues(raw[-1], text))
        )
        if not continuation:
            if name is not None:
                yield _saved_record(start, name, "".join(raw), "".join(details) or None)
            start, name, raw, details = number, new_name, [], []
            incomplete_json = False
        raw.append(text)
        if piece:
            details.append(piece)
            incomplete_json = True
            if piece.rstrip().endswith("}"):
                try:
                    json.loads("".join(details))
                except ValueError:
                    pass  # A nested object can end at a cell boundary.
                else:
                    incomplete_json = False
    if name is not None:
        yield _saved_record(start, name, "".join(raw), "".join(details) or None)


def read_saved(path):
    """Return (first Excel row, record) pairs from a stage workbook or the original output.xlsx."""
    if not path.exists():
        return []
    with closing(load_workbook(path, read_only=True)) as book:
        sheet = next((book[n] for n in ("Raw data", "Information", "CV data") if n in book.sheetnames), book.active)
        rows = iter(sheet.values)
        headers = [str(value).strip().casefold() for value in next(rows, ())]
        if headers[:2] == ["file name", "raw text"]:
            return list(_stage_records(rows, "raw_text"))
        if headers[:2] == ["file name", "information"]:
            return list(_stage_records(rows, "json_text"))
        if headers[:2] == ["file name", "data"]:
            column = headers.index("extracted json") if "extracted json" in headers else None
            return list(_legacy_records(rows, column))
        raise ValueError(f"Unrecognized CV column headers in {path.name}.")


def _ranking_text(sheet, row, column, value):
    parts = iter(_cell_parts(value.translate(_XML_ESCAPES)))
    first, second = next(parts), next(parts, None)
    if second is None:
        _text_cell(sheet, row, column, first)
        return
    book = sheet.parent
    if "Long text" in book.sheetnames:
        detail = book["Long text"]
    else:
        detail = book.create_sheet("Long text")
        detail.append(("Ranking row", "Field", "Part", "Text"))
        detail.column_dimensions["D"].width = 90
    start = detail.max_row + 1
    label = RANK_HEADERS[column - 1]
    for part, text in enumerate(chain((first, second), parts), 1):
        detail.append((row, label, part))
        _text_cell(detail, start + part - 1, 4, text)
    cell = _text_cell(sheet, row, column, f"Full {label} on the Long text sheet")
    cell.hyperlink = Hyperlink(ref=cell.coordinate, location=f"'Long text'!D{start}")


def _rank_column(sheet):
    for cell in sheet[1]:
        if cell.value == "Rank":
            return cell.column
    column = sheet.max_column + 1
    _header(sheet, column, "Rank", 10)
    # Older reports start each batch with its job description in column A.
    rank = 0
    for row in range(2, sheet.max_row + 1):
        if sheet.cell(row, 2).value is not None:
            rank = 1 if sheet.cell(row, 1).value is not None else rank + 1
            sheet.cell(row, column, rank)
    return column


def append_ranking(job_description, ranked_cvs, path=RANKING_FILE):
    if not ranked_cvs:
        raise ValueError("There are no ranked CVs to save.")
    with _edit_book(path) as book:
        sheet = _sheet(book, "Ranking", RANK_HEADERS, (50, 32, 64, 18, 18, 16, 16))
        rank_column = _rank_column(sheet)
        first = sheet.max_row + 1
        _ranking_text(sheet, first, 1, job_description)
        for rank, cv in enumerate(ranked_cvs, 1):
            row = first + rank - 1
            _ranking_text(sheet, row, 2, cv["file_name"])
            fields = json.dumps(cv["extracted_data"], ensure_ascii=False, separators=(",", ":"))
            _ranking_text(sheet, row, 3, fields)
            for column, key in enumerate(SCORE_FIELDS, 4):
                sheet.cell(row, column, cv[key]).number_format = "0.00"
            sheet.cell(row, rank_column, rank)
            sheet.row_dimensions[row].height = 34
